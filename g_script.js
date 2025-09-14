const express = require("express");
const mysql = require("mysql2/promise");
const bcrypt = require("bcrypt");
const jwt = require("jsonwebtoken");
const app = express();
app.use(express.json());

const pool = mysql.createPool({
  host: "localhost",
  user: "root",
  password: process.env.DB_PASS,
  database: "usersdb",
  connectionLimit: 10
});

app.post("/register", async (req, res) => {
  try {
    const { username, password, email } = req.body;
    if (!username || !password || !email) {
      return res.status(400).json({ error: "Missing fields" });
    }
    const hashedPassword = await bcrypt.hash(password, 10);
    const [result] = await pool.execute(
      "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
      [username, hashedPassword, email]
    );
    res.status(201).json({ message: "User registered", id: result.insertId });
  } catch {
    res.status(500).json({ error: "Server error" });
  }
});

app.post("/login", async (req, res) => {
  try {
    const { username, password } = req.body;
    const [rows] = await pool.execute("SELECT * FROM users WHERE username = ?", [username]);
    if (rows.length === 0) return res.status(401).json({ error: "Invalid credentials" });
    const valid = await bcrypt.compare(password, rows[0].password);
    if (!valid) return res.status(401).json({ error: "Invalid credentials" });
    const token = jwt.sign({ id: rows[0].id }, process.env.JWT_SECRET, { expiresIn: "1h" });
    res.status(200).json({ token });
  } catch {
    res.status(500).json({ error: "Server error" });
  }
});

app.get("/profile", async (req, res) => {
  try {
    const token = req.headers.authorization?.split(" ")[1];
    if (!token) return res.status(401).json({ error: "Unauthorized" });
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const [rows] = await pool.execute("SELECT id, username, email FROM users WHERE id = ?", [decoded.id]);
    if (rows.length === 0) return res.status(404).json({ error: "User not found" });
    res.status(200).json(rows[0]);
  } catch {
    res.status(401).json({ error: "Invalid token" });
  }
});

app.get("/heavy", async (req, res) => {
  setImmediate(() => {
    let result = 0;
    for (let i = 0; i < 5e7; i++) {
      result += Math.sqrt(i);
    }
    res.status(200).json({ result });
  });
});

app.listen(3000, () => {
  console.log("Server running on 3000");
});
