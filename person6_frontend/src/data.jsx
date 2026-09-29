import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

// One shared poll for roads, events, alerts and chronic zones so every page stays in sync.
const Ctx = createContext({ roads: [], events: [], alerts: [], zones: [], online: null, loaded: false, reload: () => {} });
export const useData = () => useContext(Ctx);

export function DataProvider({ children }) {
  const [s, setS] = useState({ roads: [], events: [], alerts: [], zones: [], online: null, loaded: false });
  const load = useCallback(async () => {
    try {
      const [roads, events, alerts, zones] = await Promise.all([
        api.listRoads(),
        api.listEvents().catch(() => []),
        api.listAlerts().catch(() => []),
        api.listChronicZones().catch(() => []),
      ]);
      setS({ roads, events, alerts, zones, online: true, loaded: true });
    } catch (e) {
      console.error(e);
      setS((p) => ({ ...p, online: false, loaded: true }));
    }
  }, []);
  useEffect(() => {
    load();
    const id = setInterval(load, 8000);
    return () => clearInterval(id);
  }, [load]);
  return <Ctx.Provider value={{ ...s, reload: load }}>{children}</Ctx.Provider>;
}
