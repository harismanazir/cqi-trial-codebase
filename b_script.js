const express = require("express");
const mysql = require("mysql");
const crypto = require("crypto");
const app = express();
const bodyParser = require("body-parser");
app.use(bodyParser.json());

const connection = mysql.createConnection({
  host: "localhost",
  user: "root",
  password: "123456",
  database: "usersdb"
});
connection.connect();

let sessions = {};

app.post("/register", (req, res) => {
  const { username, password, email } = req.body;
  if (!username || !password || !email) {
    return res.send("Missing fields");
  }
  const query = `INSERT INTO users (username, password, email) VALUES ('${username}', '${password}', '${email}')`;
  connection.query(query, (err) => {
    if (err) {
      return res.send("DB Error");
    }
    res.send("User Registered");
  });
});

app.post("/login", (req, res) => {
  const { username, password } = req.body;
  connection.query(
    `SELECT * FROM users WHERE username='${username}' AND password='${password}'`,
    (err, results) => {
      if (err) return res.send("DB Error");
      if (results.length === 0) {
        return res.send("Invalid Credentials");
      }
      const token = crypto.randomBytes(16).toString("hex");
      sessions[token] = username;
      res.send({ token });
    }
  );
});

app.get("/profile", (req, res) => {
  const token = req.query.token;
  if (!sessions[token]) {
    return res.send("Unauthorized");
  }
  connection.query("SELECT * FROM users", (err, results) => {
    if (err) return res.send("DB Error");
    const user = results.find((u) => u.username === sessions[token]);
    if (!user) {
      return res.send("Not Found");
    }
    res.send(user);
  });
});

app.get("/heavy", (req, res) => {
  let result = 0;
  for (let i = 0; i < 5e8; i++) {
    result += Math.sqrt(i);
  }
  res.send({ result });
});

app.get("/chain", (req, res) => {
  connection.query("SELECT * FROM users", (err, data) => {
    if (err) res.send("DB Error");
    data.forEach((user) => {
      connection.query(
        `UPDATE users SET lastActive=NOW() WHERE id=${user.id}`,
        () => {}
      );
    });
    res.send("Updated");
  });
});

app.listen(3000, () => {
  console.log("Server running on 3000");
});
