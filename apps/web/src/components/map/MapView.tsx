// SPDX-License-Identifier: AGPL-3.0-or-later
/// <reference types="geojson" />
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, Map as MLMap } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
// MapLibre 6 charge son worker à côté de son module : Vite doit l'emballer lui-même (lot A6, mise à jour de sécurité)
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { Commune, DumpProps, FC, Feature, LineGeom, PointGeom, PointProps, PolyGeom, QuartierProps, ReportProps, RouteProps } from '../../api/types'

maplibregl.setWorkerUrl(workerUrl)

export interface Layers {
  quartiers: boolean; dumps: boolean; reports: boolean; points: boolean; routes: boolean; trucks: boolean; sdgd?: boolean
  heat?: boolean; heatDays?: number // carte de chaleur des signalements (0 = toute la période)
  water?: boolean // retenues d'eau et dépotoirs à moins de WATER_DIST_M
}

import { MAP_KEY, WATER_DIST_M } from './mapKey'
export { MAP_KEY }
const REPORT_FILL = ['match', ['get', 'status'], 'verified', MAP_KEY.verified, 'probable', MAP_KEY.probable, 'cleaned', MAP_KEY.verified, '#ffffff']
const REPORT_STROKE = ['match', ['get', 'status'], 'to_review', MAP_KEY.review, 'rejected', MAP_KEY.rejected, 'pending', MAP_KEY.rejected, '#ffffff']
let sdgdCache: Promise<unknown> | null = null
let waterCache: Promise<unknown> | null = null
let waterDumpsCache: Promise<unknown> | null = null
// poids d'un signalement dans la carte de chaleur : un rejeté (piège, doublon) ne chauffe pas
const HEAT_WEIGHT = ['match', ['get', 'status'], 'verified', 1, 'cleaned', 0.6, 'probable', 0.8, 'to_review', 0.5, 'pending', 0.4, 0]

interface Props {
  commune: Commune | null
  quartiers?: FC<PolyGeom, QuartierProps> | null
  dumps?: FC<PointGeom, DumpProps> | null
  reports?: FC<PointGeom, ReportProps> | null
  points?: FC<PointGeom, PointProps> | null
  routes?: FC<LineGeom, RouteProps> | null
  layers: Layers
  focus?: [number, number] | null
  fitPlan?: boolean
  onDump?: (id: string) => void
  onReport?: (id: string) => void
  drawing?: boolean
  draft?: [number, number][]
  onDraftPoint?: (p: [number, number]) => void
}

const EMPTY: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

function svgImage(svg: string, size: number): Promise<HTMLImageElement> {
  return new Promise((resolve) => {
    const img = new Image(size, size)
    img.onload = () => resolve(img)
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  })
}

const DUMP_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34"><path d="M17 3 L32 30 H2 Z" fill="#dc2626" stroke="#fff" stroke-width="2.5" stroke-linejoin="round"/><rect x="15.6" y="11" width="2.8" height="10" rx="1.2" fill="#fff"/><circle cx="17" cy="25" r="1.8" fill="#fff"/></svg>`
const POINT_SVG = (ring: string) => `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" fill="#fff" stroke="${ring}" stroke-width="3.5"/><path d="M11 13.5l2.5-4h5l2.5 4M21.5 17.5l-2.5 4.5h-6M10 18l2 4" fill="none" stroke="${ring}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`
const TRUCK_HTML = (color: string, label = '') => `<div style="display:flex;align-items:center;gap:3px"><div style="width:30px;height:30px;border-radius:50%;background:${color};border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h11v10H3z"/><path d="M14 9h4l3 3v4h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/></svg></div>${label ? `<span style="background:#fff;color:${color};border:1.5px solid ${color};border-radius:6px;padding:0 5px;font:700 11px Inter,sans-serif">${label}</span>` : ''}</div>`

export function MapView(p: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const [ready, setReady] = useState(false)
  const [tilesFailed, setTilesFailed] = useState(false)
  const [base, setBase] = useState<'plan' | 'sat'>('plan')
  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    m.setLayoutProperty('sat', 'visibility', base === 'sat' ? 'visible' : 'none')
    m.setLayoutProperty('osm', 'visibility', base === 'sat' ? 'none' : 'visible')
  }, [base, ready])
  const cb = useRef(p)
  cb.current = p

  useEffect(() => {
    if (!ref.current || map.current) return
    const m = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        sources: {
          osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, maxzoom: 19,
                 attribution: '© contributeurs OpenStreetMap' },
          sat: { type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'], tileSize: 256, maxzoom: 19,
                 attribution: 'Imagerie © Esri, Maxar, Earthstar Geographics' },
        },
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': '#ebe5d6' } },
          { id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-saturation': -0.35 } },
          { id: 'sat', type: 'raster', source: 'sat', layout: { visibility: 'none' }, paint: { 'raster-saturation': -0.2, 'raster-brightness-max': 0.85 } },
        ],
      },
      center: [-1.52, 12.37], zoom: 11.3, attributionControl: { compact: true },
    })
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    m.addControl(new maplibregl.FullscreenControl(), 'top-right')
    m.on('error', (e) => { if (String(e.error?.message ?? '').includes('tile')) setTilesFailed(true) })
    let initialised = false
    const init = async () => {
      if (initialised) return
      initialised = true
      m.addImage('dump', await svgImage(DUMP_SVG, 34), { pixelRatio: 1.4 })
      m.addImage('point', await svgImage(POINT_SVG(MAP_KEY.plan), 32), { pixelRatio: 1.5 })
      m.addImage('point-bad', await svgImage(POINT_SVG(MAP_KEY.problem), 32), { pixelRatio: 1.5 })
      for (const id of ['quartiers', 'routes', 'depot-link', 'points', 'dumps', 'reports', 'draft', 'sdgd', 'heat', 'water', 'water-dumps']) m.addSource(id, { type: 'geojson', data: EMPTY })
      m.addLayer({ id: 'q-fill', type: 'fill', source: 'quartiers', paint: { 'fill-color': MAP_KEY.zone, 'fill-opacity': 0.03 } })
      m.addLayer({ id: 'q-line', type: 'line', source: 'quartiers', paint: { 'line-color': MAP_KEY.zone, 'line-width': 1.2, 'line-opacity': 0.6, 'line-dasharray': [3, 2] } })
      m.addLayer({ id: 'water-fill', type: 'fill', source: 'water', paint: { 'fill-color': '#29b6f6', 'fill-opacity': 0.45 } })
      m.addLayer({ id: 'water-line', type: 'line', source: 'water', paint: { 'line-color': '#0277bd', 'line-width': 1.6 } })
      m.addLayer({ id: 'heat', type: 'heatmap', source: 'heat', paint: {
        'heatmap-weight': HEAT_WEIGHT as never,
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 10, 0.8, 15, 2],
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 14, 13, 24, 16, 40],
        'heatmap-opacity': 0.8,
        'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(33,102,172,0)', 0.15, '#4fc3f7', 0.35, '#26a69a',
          0.55, '#fdd835', 0.75, '#fb8c00', 1, '#d32f2f'] } })
      m.addLayer({ id: 'depot-link', type: 'line', source: 'depot-link', layout: { 'line-cap': 'round' }, paint: { 'line-color': MAP_KEY.plan, 'line-width': 2, 'line-opacity': 0.6, 'line-dasharray': [2, 2] } })
      m.addLayer({ id: 'routes-casing', type: 'line', source: 'routes', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#fff', 'line-width': 5, 'line-opacity': 0.8 } })
      m.addLayer({ id: 'routes', type: 'line', source: 'routes', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': MAP_KEY.plan, 'line-width': 2.5, 'line-opacity': 0.75 } })
      m.addLayer({ id: 'routes-hl', type: 'line', source: 'routes', filter: ['==', ['get', 'id'], ''], layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': MAP_KEY.plan, 'line-width': 6 } })
      m.addLayer({ id: 'sdgd', type: 'circle', source: 'sdgd', paint: {
        // même teinte (référence) ; la forme dit le type : CCT plein, décharge = anneau, CTVD = grand anneau
        'circle-radius': ['match', ['get', 'statut'], 'ctvd', 10, 'cct', 5.5, 6.5],
        'circle-color': MAP_KEY.reference, 'circle-opacity': ['match', ['get', 'statut'], 'cct', 0.9, 0.08],
        'circle-stroke-color': MAP_KEY.reference, 'circle-stroke-width': ['match', ['get', 'statut'], 'cct', 1.5, 2.5] } })
      m.addLayer({ id: 'reports', type: 'circle', source: 'reports', paint: { 'circle-radius': 4.5, 'circle-color': REPORT_FILL as never, 'circle-stroke-color': REPORT_STROKE as never, 'circle-stroke-width': 1.8 } })
      m.addLayer({ id: 'points', type: 'symbol', source: 'points', layout: { 'icon-image': ['case', ['get', 'unserved'], 'point-bad', 'point'], 'icon-allow-overlap': true, 'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.55, 14, 0.9] } })
      m.addLayer({ id: 'water-dumps', type: 'circle', source: 'water-dumps', paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 9, 15, 18],
        'circle-color': 'rgba(41,182,246,0.18)', 'circle-stroke-color': '#0277bd', 'circle-stroke-width': 2.5 } })
      m.addLayer({ id: 'dumps', type: 'symbol', source: 'dumps', layout: { 'icon-image': 'dump', 'icon-allow-overlap': true, 'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.5, 14, 0.9] } })
      m.addLayer({ id: 'draft-fill', type: 'fill', source: 'draft', paint: { 'fill-color': '#f28c28', 'fill-opacity': 0.2 } })
      m.addLayer({ id: 'draft-line', type: 'line', source: 'draft', paint: { 'line-color': '#f28c28', 'line-width': 3 } })
      m.on('click', 'dumps', (e) => { const id = e.features?.[0]?.properties?.id; if (id) cb.current.onDump?.(String(id)) })
      m.on('click', 'reports', (e) => { const id = e.features?.[0]?.properties?.id; if (id) cb.current.onReport?.(String(id)) })
      m.on('click', (e) => { if (cb.current.drawing) cb.current.onDraftPoint?.([e.lngLat.lng, e.lngLat.lat]) })
      for (const l of ['dumps', 'reports']) {
        m.on('mouseenter', l, () => { m.getCanvas().style.cursor = 'pointer' })
        m.on('mouseleave', l, () => { m.getCanvas().style.cursor = '' })
      }
      const popup = new maplibregl.Popup({ closeButton: false, offset: 12 })
      m.on('mousemove', 'points', (e) => {
        const f = e.features?.[0]?.properties
        if (!f) return
        popup.setLngLat(e.lngLat).setHTML(`<b>${String(f.key).startsWith('CCT-') ? `Centre de collecte existant ${f.key} (SDGD 2020)` : `Point ${f.key}`}</b><br/>${Number(f.demand_t_week).toFixed(1)} t/semaine · capacité ${f.capacity_t} t${f.unserved ? '<br/><b style="color:#dc2626">Non desservi</b>' : ''}`).addTo(m)
      })
      m.on('mouseleave', 'points', () => popup.remove())
      m.on('mousemove', 'routes', (e) => {
        const f = e.features?.[0]?.properties
        if (!f) return
        m.setFilter('routes-hl', ['==', ['get', 'id'], f.id])
        popup.setLngLat(e.lngLat).setHTML(`<b>Tournée ${f.vehicle_label}</b> · rotation ${f.rotation}<br/>${Number(f.distance_km).toFixed(1)} km · ${Number(f.load_t).toFixed(1)} / ${f.capacity_t} t`).addTo(m)
      })
      m.on('mouseleave', 'routes', () => { m.setFilter('routes-hl', ['==', ['get', 'id'], '']); popup.remove() })
      const KIND: Record<string, string> = { sauvage: 'Dépôt sauvage', encadree: 'Décharge encadrée (DSPH)', autre: 'Autre site de dépôt' }
      m.on('mousemove', 'dumps', (e) => {
        const f = e.features?.[0]?.properties
        if (f) popup.setLngLat(e.lngLat).setHTML(`<b>${KIND[f.site_kind] ?? 'Dépôt sauvage'}</b><br/>${f.ref && f.ref !== 'null' ? `Réf. ${f.ref}` : `${f.n_reports} signalement(s) citoyen(s)`}`).addTo(m)
      })
      m.on('mouseleave', 'dumps', () => popup.remove())
      m.on('mousemove', 'sdgd', (e) => {
        const f = e.features?.[0]?.properties
        if (f) popup.setLngLat(e.lngLat).setHTML(`<b>${f.libelle}</b><br/>Réf. SDGD 2020 · n° ${String(f.id).split('-').pop()} (relevé 2019)<br/><span style="color:#64748b">Position numérisée, ± ${f.precision_m} m</span>`).addTo(m)
      })
      m.on('mouseleave', 'sdgd', () => popup.remove())
      m.on('mousemove', 'water-dumps', (e) => {
        const f = e.features?.[0]?.properties
        if (f && !m.queryRenderedFeatures(e.point, { layers: ['dumps'] }).length) popup.setLngLat(e.lngLat).setHTML(`<b>Dépotoir à ${f.distance_m} m d'une retenue d'eau</b><br/>${f.retenue}${f.caniveau ? '<br/><b style="color:#c62828">Dans un caniveau</b>' : ''}`).addTo(m)
      })
      m.on('mouseleave', 'water-dumps', () => popup.remove())
      m.on('mousemove', 'water-fill', (e) => {
        if (m.queryRenderedFeatures(e.point, { layers: ['points', 'dumps', 'reports', 'water-dumps'] }).length) return
        const f = e.features?.[0]?.properties
        if (f) popup.setLngLat(e.lngLat).setHTML(`<b>${f.nom}</b><br/>${f.surface_ha} ha · © OpenStreetMap`).addTo(m)
      })
      m.on('mouseleave', 'water-fill', () => popup.remove())
      m.on('mousemove', 'q-fill', (e) => {
        if (m.queryRenderedFeatures(e.point, { layers: ['points', 'dumps', 'reports'] }).length) return
        const f = e.features?.[0]?.properties
        if (f) popup.setLngLat(e.lngLat).setHTML(`<b>${f.name}</b><br/>${Number(f.population).toLocaleString('fr-FR')} habitants`).addTo(m)
      })
      m.on('mouseleave', 'q-fill', () => popup.remove())
      setReady(true)
      // modules optionnels (docs/MODULES.md) : ils ajoutent leurs couches à cette carte
      ;(window as unknown as { __salubriMap?: MLMap }).__salubriMap = m
      window.dispatchEvent(new Event('salubri:map-ready'))
    }
    // 'style.load' fires even when the tile server is unreachable (offline room), unlike 'load'.
    m.once('style.load', () => { void init() })
    m.once('load', () => { void init() })
    map.current = m
    return () => { m.remove(); map.current = null }
  }, [])

  useEffect(() => {
    if (!map.current || !p.commune) return
    const [x0, y0, x1, y1] = p.commune.bbox
    const [dx, dy] = p.commune.depot
    map.current.fitBounds([Math.min(x0, dx), Math.min(y0, dy), Math.max(x1, dx), Math.max(y1, dy)], { padding: 40, duration: 0 })
  }, [p.commune])

  useEffect(() => {
    if (map.current && p.focus) map.current.flyTo({ center: p.focus, zoom: 15 })
  }, [p.focus])

  const planKey = p.points?.features.map((f) => f.properties.key).join() ?? ''
  useEffect(() => {
    const f = p.points?.features ?? []
    if (!map.current || !p.fitPlan || f.length < 2) return
    const xs = f.map((x) => x.geometry.coordinates[0])
    const ys = f.map((x) => x.geometry.coordinates[1])
    map.current.fitBounds([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], { padding: 60, duration: 600 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planKey, p.fitPlan, ready])

  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    const set = (id: string, data: unknown) => (m.getSource(id) as GeoJSONSource).setData((data ?? EMPTY) as GeoJSON.GeoJSON)
    set('quartiers', p.layers.quartiers ? p.quartiers : null)
    if (p.layers.sdgd) {
      sdgdCache ??= fetch('/sdgd/sdgd2020.geojson').then((r) => r.json()).catch(() => null)
      void sdgdCache.then((d) => { if (map.current === m) set('sdgd', d) })
    } else set('sdgd', null)
    set('dumps', p.layers.dumps ? p.dumps : null)
    if (p.layers.heat && p.reports) {
      const since = p.layers.heatDays ? Date.now() - p.layers.heatDays * 86400000 : 0
      set('heat', { ...p.reports, features: p.reports.features.filter((f) => new Date(f.properties.reported_at).getTime() >= since) })
    } else set('heat', null)
    if (p.layers.water) {
      waterCache ??= api.water().catch(() => null)
      waterDumpsCache ??= api.waterDumps(WATER_DIST_M).then((d) => ({ type: 'FeatureCollection', features: d.sites.map((x) => ({
        type: 'Feature', properties: x, geometry: { type: 'Point', coordinates: [x.lon, x.lat] } })) })).catch(() => null)
      void waterCache.then((d) => { if (map.current === m) set('water', d) })
      void waterDumpsCache.then((d) => { if (map.current === m) set('water-dumps', d) })
    } else { set('water', null); set('water-dumps', null) }
    set('points', p.layers.points ? p.points : null)
    set('reports', p.layers.reports ? p.reports : null)
    // Sans OSRM, une tournée = [dépôt, arrêts…, dépôt] en lignes droites : on retire les trajets dépôt
    // (sinon éventail de traits à travers la ville) et on les remplace par une seule liaison en pointillés.
    const inner = (f: Feature<LineGeom, RouteProps>) => {
      const c = f.geometry.coordinates
      return c.length === f.properties.stops.length + 2 && c.length > 3 ? c.slice(1, -1) : c
    }
    set('routes', p.layers.routes && p.routes ? {
      ...p.routes, features: p.routes.features.map((f) => ({ ...f, geometry: { ...f.geometry, coordinates: inner(f) }, properties: { ...f.properties, id: f.properties.id ?? f.id } })),
    } : null)
    const allStops = (p.routes?.features ?? []).flatMap((f) => inner(f))
    set('depot-link', p.layers.routes && p.commune && allStops.length ? {
      type: 'FeatureCollection', features: [{ type: 'Feature', properties: { label: 'Navettes vers le dépôt' }, geometry: { type: 'LineString', coordinates: [
        p.commune.depot, [allStops.reduce((s, c) => s + c[0], 0) / allStops.length, allStops.reduce((s, c) => s + c[1], 0) / allStops.length]] } }],
    } : null)
    markers.current.forEach((mk) => mk.remove())
    markers.current = []
    if (p.layers.trucks && p.routes) {
      const seen = new Set<string>()
      for (const f of p.routes.features) {
        if (seen.has(f.properties.vehicle_label)) continue
        seen.add(f.properties.vehicle_label)
        const c = f.geometry.coordinates
        const ic = inner(f)
        const at = ic[Math.floor(ic.length / 2)] ?? c[0]
        const el = document.createElement('div')
        el.innerHTML = TRUCK_HTML(MAP_KEY.plan, f.properties.vehicle_label)
        el.title = `${f.properties.vehicle_label} — ${f.properties.load_t.toFixed(1)} / ${f.properties.capacity_t} t`
        markers.current.push(new maplibregl.Marker({ element: el }).setLngLat(at).addTo(m))
      }
    }
    if (p.commune) {
      const el = document.createElement('div')
      el.innerHTML = `<div title="Dépôt des camions" style="background:#0f2b55;color:#fff;border-radius:8px;padding:3px 7px;font:700 11px Inter;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)">DÉPÔT</div>`
      markers.current.push(new maplibregl.Marker({ element: el }).setLngLat(p.commune.depot).addTo(m))
    }
  }, [ready, p.quartiers, p.dumps, p.points, p.routes, p.reports, p.layers, p.commune])

  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    const d = p.draft ?? []
    const data = d.length >= 3
      ? { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[...d, d[0]]] } }
      : { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: d.length ? d : [] } }
    ;(m.getSource('draft') as GeoJSONSource).setData(data as GeoJSON.GeoJSON)
    m.getCanvas().style.cursor = p.drawing ? 'crosshair' : ''
  }, [ready, p.draft, p.drawing])

  return (
    <>
      <div ref={ref} className="map" />
      <div className="basemap-switch" role="group" aria-label="Fond de carte">
        <button className={base === 'plan' ? 'on' : ''} onClick={() => setBase('plan')}>Plan</button>
        <button className={base === 'sat' ? 'on' : ''} onClick={() => setBase('sat')}>Satellite</button>
      </div>
      {tilesFailed && <div className="map-banner">Fond de carte indisponible (pas d'Internet) : les couches Salubri restent affichées.</div>}
    </>
  )
}
