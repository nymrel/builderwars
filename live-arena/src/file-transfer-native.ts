import { Filesystem, Directory } from "@capacitor/filesystem";
import { Share } from "@capacitor/share";
import { EXPORT_CACHE, type NativeFilePort } from "./file-transfer";

// App-private cache only. No external-storage permission, arbitrary URI read or HTTP download.
export const nativeFilePort: NativeFilePort = {
  async list() {
    try { await Filesystem.mkdir({ path: EXPORT_CACHE, directory: Directory.Cache, recursive: false }); }
    catch { /* Existing directory is normal; readdir below must still succeed. */ }
    try {
      const result = await Filesystem.readdir({ path: EXPORT_CACHE, directory: Directory.Cache });
      return result.files.map(({ name, type, size, mtime }) => ({ name, type, size, mtime }));
    } catch { throw Error("Export cache is unavailable. No share sheet was opened."); }
  },
  async write(name, data) {
    try { return (await Filesystem.writeFile({ path: `${EXPORT_CACHE}/${name}`, data, directory: Directory.Cache })).uri; }
    catch { throw Error("Could not prepare the export file. No share sheet was opened."); }
  },
  async remove(name) { await Filesystem.deleteFile({ path: `${EXPORT_CACHE}/${name}`, directory: Directory.Cache }); },
  async share(value) {
    try { await Share.share({ ...value, title: "BuilderWars", dialogTitle: "Save or share BuilderWars file" }); return "sheet-closed"; }
    catch (error) {
      // Exact documented implementation outcome; other errors do not prove cancellation.
      if ((error as { message?: unknown })?.message === "Share canceled") return "cancelled";
      throw Error("The share sheet could not confirm a handoff. Check your destination before trying again.");
    }
  },
};
