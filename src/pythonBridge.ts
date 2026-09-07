import { spawn } from "child_process";

export interface PythonRpcResponse {
  [key: string]: any;
}

/**
 * Executes a command in the pure Python 3 backend.
 * Streams JSON payload via stdin and parses stdout.
 */
export async function callPythonBackend(payload: Record<string, any>): Promise<any> {
  return new Promise((resolve, reject) => {
    const py = spawn("python3", ["-m", "backend.runner"], {
      cwd: process.cwd(),
      env: { ...process.env, PYTHONPATH: process.cwd() },
    });

    let stdout = "";
    let stderr = "";

    py.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    py.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    py.on("close", (code) => {
      if (code !== 0) {
        return reject(new Error(`Python backend process exited with code ${code}: ${stderr}`));
      }
      try {
        const parsed = JSON.parse(stdout.trim());
        resolve(parsed);
      } catch (err: any) {
        reject(new Error(`Failed to parse Python response: ${stdout} (Error: ${err.message})`));
      }
    });

    py.stdin.write(JSON.stringify(payload));
    py.stdin.end();
  });
}
