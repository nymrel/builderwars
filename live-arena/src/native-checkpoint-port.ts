import { Filesystem, Directory, Encoding } from "@capacitor/filesystem";
import { CHECKPOINT_DIRECTORY, type CheckpointPort } from "./native-checkpoint";

const path = (name: string) => {
  if (!/^checkpoint-[1-9][0-9]{0,15}-[a-f0-9-]{36}\.json(?:\.part)?$/.test(name))
    throw Error("Invalid native checkpoint filename.");
  return `${CHECKPOINT_DIRECTORY}/${name}`;
};
// Persistent app-private Data, not the export Cache or external/shared storage.
// No URL, arbitrary path, provider credential or remote download entrypoint.
export const nativeCheckpointPort: CheckpointPort = {
  async list() {
    try { await Filesystem.mkdir({ path: CHECKPOINT_DIRECTORY, directory: Directory.Data }); }
    catch { /* Existing directory is normal; the following read must still succeed. */ }
    return (await Filesystem.readdir({ path: CHECKPOINT_DIRECTORY, directory: Directory.Data })).files
      .map(({ name, type, size }) => ({ name, type, size }));
  },
  async read(name) {
    const { data } = await Filesystem.readFile({ path: path(name), directory: Directory.Data, encoding: Encoding.UTF8 });
    if (typeof data !== "string") throw Error("Native checkpoint did not contain text.");
    return data;
  },
  async write(name, data) { await Filesystem.writeFile({ path: path(name), directory: Directory.Data, encoding: Encoding.UTF8, data }); },
  async promote(from, to) { await Filesystem.rename({ from: path(from), to: path(to), directory: Directory.Data, toDirectory: Directory.Data }); },
  async remove(name) { await Filesystem.deleteFile({ path: path(name), directory: Directory.Data }); },
};
