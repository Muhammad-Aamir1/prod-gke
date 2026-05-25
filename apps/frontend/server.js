const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const client = require('prom-client');

client.collectDefaultMetrics();

const app = express();
const PORT = 8080;
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend-svc.prod-ns.svc.cluster.local:8080';

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

app.use('/api', createProxyMiddleware({ target: BACKEND_URL, changeOrigin: true }));
app.use(express.static('public'));

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'frontend' });
});

app.listen(PORT, () => {
  console.log(`Frontend listening on port ${PORT}`);
});
