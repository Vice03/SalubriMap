-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Rainy season: official car profile, every speed x0.7, unpaved roads and tracks almost impassable.
package.path = '/opt/?.lua;' .. package.path
local car = require('car')

local FACTOR = tonumber(os.getenv('SALUBRI_RAIN_FACTOR') or '0.7')
local MUDDY = { unpaved = true, ground = true, dirt = true, earth = true, sand = true, mud = true, gravel = true }

local function scale(result, f)
  if result.forward_speed and result.forward_speed > 0 then result.forward_speed = result.forward_speed * f end
  if result.backward_speed and result.backward_speed > 0 then result.backward_speed = result.backward_speed * f end
  if result.forward_rate and result.forward_rate > 0 then result.forward_rate = result.forward_rate * f end
  if result.backward_rate and result.backward_rate > 0 then result.backward_rate = result.backward_rate * f end
end

local function process_way(profile, way, result, relations)
  car.process_way(profile, way, result, relations)
  local surface = way:get_value_by_key('surface')
  local highway = way:get_value_by_key('highway')
  if (surface and MUDDY[surface]) or highway == 'track' then
    scale(result, 0.05)
  else
    scale(result, FACTOR)
  end
end

return {
  setup = car.setup,
  process_way = process_way,
  process_node = car.process_node,
  process_turn = car.process_turn,
}
