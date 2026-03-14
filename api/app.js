// api/chat.js
import sqlite3 from "sqlite3";
import { open } from "sqlite";
import { Mistral } from "mistralai";
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

  const count = await db.get("SELECT COUNT(*) as count FROM college_info");
  if (count.count === 0) {
    const initialData = [
      ["fees", "Fees can be paid in the college office.<br>Office Timing: 8:30 AM – 1:30 PM (Monday to Friday)"],
      ["admission", "Admission details are available in the admission office."],
      ["department", "We offer BSc, BCom, BBA, BA and many departments."]
    ];
    const stmt = await db.prepare("INSERT INTO college_info (keyword,response) VALUES (?,?)");
    for (let row of initialData) await stmt.run(row);
    await stmt.finalize();
  }
}
await initDB();

const client = new Mistral({ api_key: process.env.MISTRAL_API_KEY });

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).send("Method Not Allowed");

  const body = await json(req);
  if (!body || !body.message) return res.status(400).json({ reply: "Invalid request" });

  const userMessage = body.message.toLowerCase();
  const rows = await db.all("SELECT keyword, response FROM college_info");
  const words = userMessage.replace(/[?,]/g, "").split(" ");
  const replies = rows.filter(r => words.includes(r.keyword.toLowerCase())).map(r => r.response);

  let finalReply = "";

  if (replies.length > 0) {
    finalReply = replies.join("<br><br>");
  } else {
    const systemPrompt = `
You are IGRIZ, a professional and friendly college AI assistant for
Hindusthan College of Arts & Science (HICAS) in Coimbatore.

Give clear, short answers to students about admissions, fees, courses,
campus facilities and events.

Use simple English.

If the user message contains Tamil words or script
(டா, எவ்ளோ, கல்லூரி, ஃபீஸ் etc), reply in friendly Tamil or Tamlish.
`;

    const messages = [{ role: "system", content: systemPrompt }];
    messages.push({ role: "user", content: userMessage });

    try {
      const response = await client.chat.complete({
        model: "mistral-small-latest",
        messages
      });
      finalReply = response.choices[0].message.content.replace(/\n/g, "<br>");
    } catch (err) {
      console.error("Mistral error:", err);
      finalReply = "AI server busy da. Try again later.";
    }
  }

  res.status(200).json({ reply: finalReply });
}