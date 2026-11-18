// SPDX-License-Identifier: AGPL-3.0-or-later
import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'bf.salubri.go',
  appName: 'Salubri Go',
  webDir: 'dist/native',
  plugins: { CapacitorHttp: { enabled: true } }, // appels /api vers http://<LAN> hors du WebView : ni contenu mixte ni CORS
}
export default config
