const express = require('express');
const { Pool } = require('pg');
const Redis = require('ioredis');
const client = require('prom-client');

client.collectDefaultMetrics();

const app = express();
const PORT = 8080;

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

const pool = new Pool({
  host: process.env.PGHOST || 'postgres',
  port: parseInt(process.env.PGPORT || '5432'),
  user: process.env.PGUSER || 'admin',
  password: process.env.PGPASSWORD || 'admin',
  database: process.env.PGDATABASE || 'appdb',
  connectionTimeoutMillis: 3000,
});

const redis = new Redis({
  host: process.env.REDIS_HOST || 'redis',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  connectTimeout: 3000,
  maxRetriesPerRequest: 1,
  lazyConnect: true,
});
redis.on('error', () => {});

app.get('/health', async (req, res) => {
  const result = { status: 'ok', service: 'backend' };
  try {
    const pgRes = await pool.query('SELECT NOW()');
    result.postgres = pgRes.rows[0].now;
  } catch (e) {
    result.postgres = 'error: ' + e.message;
  }
  try {
    await redis.ping();
    result.redis = 'connected';
  } catch (e) {
    result.redis = 'error: ' + e.message;
  }
  res.json(result);
});

app.get('/data', async (req, res) => {
  try {
    const result = await pool.query('SELECT NOW() AS time, $1::text AS message', ['Hello from prod-gke backend!']);
    res.json(result.rows[0]);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`Backend listening on port ${PORT}`);
});
