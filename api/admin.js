// api/admin.js
import sqlite3 from "sqlite3";
import { open } from "sqlite";
import { json } from "micro";

const DB_PATH = "./igriz.db";
let db;

async function initDB() {
  if (db) return;
  db = await open({ filename: DB_PATH, driver: sqlite3.Database });
  await db.exec(`
    CREATE TABLE IF NOT EXISTS college_info (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      keyword TEXT UNIQUE,
      response TEXT
    )
  `);
}
await initDB();

// Simple admin password check (change for production)
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "15012006";

export default async function handler(req, res) {
  const url = req.url.split("?")[0];

  if (req.method === "POST") {
    const body = await json(req);

    // Login
    if (url === "/api/admin/login") {
      if (body.password === ADMIN_PASSWORD) {
        res.status(200).json({ success: true });
      } else {
        res.status(401).json({ success: false, message: "Wrong password" });
      }
      return;
    }

    // Save keyword/response
    if (url === "/api/admin/save") {
      const { keyword, response } = body;
      const existing = await db.get("SELECT * FROM college_info WHERE keyword=?", [keyword]);

      if (existing) {
        await db.run("UPDATE college_info SET response=? WHERE keyword=?", [response, keyword]);
      } else {
        await db.run("INSERT INTO college_info (keyword,response) VALUES (?,?)", [keyword, response]);
      }
      res.status(200).json({ success: true });
      return;
    }

    // Delete keyword
    if (url === "/api/admin/delete") {
      const { keyword } = body;
      await db.run("DELETE FROM college_info WHERE keyword=?", [keyword]);
      res.status(200).json({ success: true });
      return;
    }

    res.status(404).json({ message: "Not found" });
    return;
  }

  // GET existing keywords
  if (req.method === "GET" && url === "/api/admin/keywords") {
    const rows = await db.all("SELECT keyword FROM college_info");
    res.status(200).json({ keywords: rows });
    return;
  }

  res.status(405).json({ message: "Method not allowed" });
}