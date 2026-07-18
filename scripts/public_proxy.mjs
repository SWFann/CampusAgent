#!/usr/bin/env node
import http from "node:http";
import net from "node:net";
import { URL } from "node:url";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 2) {
  args.set(process.argv[index], process.argv[index + 1]);
}

const webTarget = new URL(args.get("--web") ?? "http://127.0.0.1:3000");
const apiTarget = new URL(args.get("--api") ?? "http://127.0.0.1:8000");
const listenPort = Number(args.get("--port") ?? "8787");
const listenHost = args.get("--host") ?? "127.0.0.1";

function isApiPath(pathname) {
  return (
    pathname.startsWith("/api/") ||
    pathname === "/api" ||
    pathname.startsWith("/docs") ||
    pathname.startsWith("/redoc") ||
    pathname.startsWith("/openapi.json") ||
    pathname.startsWith("/health") ||
    pathname.startsWith("/metrics")
  );
}

function targetFor(pathname) {
  return isApiPath(pathname) ? apiTarget : webTarget;
}

function proxyHttp(req, res) {
  const pathname = new URL(req.url ?? "/", "http://local").pathname;
  const target = targetFor(pathname);
  const headers = { ...req.headers, host: target.host };

  const upstream = http.request(
    {
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port,
      method: req.method,
      path: req.url,
      headers,
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode ?? 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    },
  );

  upstream.on("error", (error) => {
    res.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
    res.end(`CampusAgent public proxy upstream error: ${error.message}\n`);
  });

  req.pipe(upstream);
}

function proxyWebSocket(req, socket, head) {
  const pathname = new URL(req.url ?? "/", "http://local").pathname;
  const target = targetFor(pathname);
  const upstream = net.connect(Number(target.port), target.hostname, () => {
    const lines = [`${req.method} ${req.url} HTTP/${req.httpVersion}`];
    for (const [key, value] of Object.entries(req.headers)) {
      if (value === undefined) continue;
      if (Array.isArray(value)) {
        for (const item of value) lines.push(`${key}: ${item}`);
      } else if (key.toLowerCase() === "host") {
        lines.push(`host: ${target.host}`);
      } else {
        lines.push(`${key}: ${value}`);
      }
    }
    lines.push("", "");
    upstream.write(lines.join("\r\n"));
    if (head.length > 0) upstream.write(head);
    upstream.pipe(socket);
    socket.pipe(upstream);
  });

  upstream.on("error", () => {
    socket.destroy();
  });
}

const server = http.createServer(proxyHttp);
server.on("upgrade", proxyWebSocket);
server.listen(listenPort, listenHost, () => {
  console.log(`[CampusAgent public proxy] web -> ${webTarget.href}`);
  console.log(`[CampusAgent public proxy] api -> ${apiTarget.href}`);
  console.log(`[CampusAgent public proxy] listening on http://${listenHost}:${listenPort}`);
});
