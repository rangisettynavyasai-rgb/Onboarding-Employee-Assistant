import { initializeApp, getApps, cert } from "firebase-admin/app";
import { getFirestore, Firestore } from "firebase-admin/firestore";
import fs from "fs";
import path from "path";

let dbInstance: Firestore | null = null;

export function getFirestoreDb(): Firestore | null {
  if (dbInstance) return dbInstance;

  try {
    const configPath = path.join(process.cwd(), "firebase-applet-config.json");
    let projectId = process.env.FIREBASE_PROJECT_ID || process.env.GCP_PROJECT_ID || "patchamomma-505416";
    let databaseId = "ai-studio-onboardingemploy-b1158660-8824-4e90-b842-3a0f086d1796";

    if (fs.existsSync(configPath)) {
      try {
        const raw = fs.readFileSync(configPath, "utf-8");
        const cfg = JSON.parse(raw);
        if (cfg.projectId) projectId = cfg.projectId;
        if (cfg.firestoreDatabaseId) databaseId = cfg.firestoreDatabaseId;
      } catch (err) {
        console.warn("Could not read firebase-applet-config.json:", err);
      }
    }

    if (!getApps().length) {
      initializeApp({
        projectId: projectId,
      });
    }

    // Connect to specific databaseId provisioned for this applet
    dbInstance = getFirestore(databaseId);
    console.log(`Connected to Firestore (project: ${projectId}, database: ${databaseId})`);
    return dbInstance;
  } catch (err) {
    console.warn("Firestore initialization error, running in memory-fallback mode:", err);
    return null;
  }
}
