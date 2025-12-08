# Innova Butler - Development Roadmap

## Goal
Integrate Innova Butler thermostats into Home Assistant with full climate control.

## API Overview

**Endpoint:** `http://{host}/installedplugin/com.innova.ambiente/2.0/server/index.php?Action=getHomepage`

**Data path:** `RESULT.user.homes[].rooms[].devices{}`

**Device fields (FCL485):**
| Field | Description | Example |
|-------|-------------|---------|
| `uid` | Device unique ID | `d61a6f0c-2677-...` |
| `name` | Device name | `Soggiorno` |
| `tempRoom` | Current temperature | `19.4` |
| `tempSet` | Target temperature | `20` |
| `standBy.value` | Standby state | `0` / "true" |
| `min` / `max` | Temp range | `5` / `40` |
| `mode` | 0=heating, 1=cooling | `0` |
| `connectionStatus.status` | Connection | `1`=OK, `2`=error |

**Your devices:**
- Tavernetta, Soggiorno, Camera matrimoniale, Cameretta, Studio, Mansarda

---

## Phase 1: Read-Only Climate Entities ✅ COMPLETED

Create climate entities that display current state (no control yet).

### Tasks
- [x] 1.1 Create `api.py` - API client class with async HTTP calls
- [x] 1.2 Create `coordinator.py` - DataUpdateCoordinator for polling (60s interval)
- [x] 1.3 Update `const.py` - Add constants (DOMAIN, platforms, defaults)
- [x] 1.4 Create `config_flow.py` - UI configuration for host IP
- [x] 1.5 Update `__init__.py` - Integration setup with coordinator
- [x] 1.6 Create `climate.py` - ClimateEntity with:
  - Current temperature (`tempRoom`)
  - Target temperature (`tempSet`)
  - HVAC mode based on `standBy` and home `mode`
- [x] 1.7 Update `manifest.json` - Add dependencies and version
- [x] 1.8 Test in Home Assistant

### Result
Climate cards showing each thermostat with current/target temps (read-only).

---

## Phase 2: Climate Control ⬅️ NEXT

Add ability to change temperature and modes.

### Pre-requisite: Discover Control API
We have discovered the `setSetPoint` action for temperature control and `powerOffDevice` (and assumed `powerOnDevice`) for device power control. Preset mode control is not supported at the device level.

### Tasks
- [x] 2.1 Document the control API endpoint(s) (for temperature and power)
- [x] 2.2 Add `set_temperature()` to API client
- [x] 2.3 Add On/Off function to API client (`powerOnDevice` / `powerOffDevice`)
- [ ] 2.4 Add `set_preset_mode()` to API client (fan function) - *Cancelled: Not supported at device level*
- [x] 2.5 Implement climate entity control methods:
  - `async_set_temperature()`
  - `async_set_hvac_mode()` (used for On/Off control)
  - `async_set_preset_mode()` - *Cancelled: Not supported at device level*
- [ ] 2.6 Test all control functions

### Expected Result
Full climate control (temperature and on/off) from Home Assistant UI and automations.

---

## Phase 3: Additional Features

### Optional Enhancements
- [ ] 3.1 Add sensor entities for extra data:
  - Connection status sensor
  - Alarm binary sensors
- [ ] 3.2 Device grouping by room in HA device registry
- [ ] 3.3 HACS compatibility (already have `hacs.json`)
- [ ] 3.4 Handle multiple homes (if applicable)
- [ ] 3.5 Add Italian translations (`strings.json`)

---

## File Structure

```
custom_components/innova_butler/
├── __init__.py          # Integration setup
├── api.py               # API client
├── climate.py           # Climate entities
├── config_flow.py       # UI configuration
├── const.py             # Constants
├── coordinator.py       # Data coordinator
├── manifest.json        # Component metadata
└── strings.json         # Translations
```

---

## Next Step

**Test the implemented control functions** for temperature setting and device on/off in Home Assistant. This will complete Phase 2.
