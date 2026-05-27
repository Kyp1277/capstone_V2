const http = require("http");
const fs = require("fs");
const path = require("path");

// Server statis kecil untuk preview frontend tanpa framework/build tool.
const root = __dirname;
const port = Number(process.env.PORT || 4173);
const apiTarget = new URL(process.env.API_TARGET || "http://127.0.0.1:5000");

// Mapping ekstensi file ke Content-Type agar browser membaca asset dengan benar.
const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg"
};

const server = http.createServer((request, response) => {
  const requestUrl = new URL(request.url, `http://${request.headers.host}`);

  if (requestUrl.pathname === "/health" || requestUrl.pathname.startsWith("/api/")) {
    proxyApiRequest(request, response, requestUrl);
    return;
  }

  const pathname = requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname;

  // Normalisasi path mencegah request keluar dari folder project.
  const safePath = path
    .normalize(decodeURIComponent(pathname))
    .replace(/^[/\\]+/, "")
    .replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(root, safePath);

  if (!filePath.startsWith(root)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }

    response.writeHead(200, {
      "content-type": types[path.extname(filePath)] || "application/octet-stream",
      // Saat development, cache dimatikan supaya perubahan file langsung terlihat.
      "cache-control": "no-store, max-age=0"
    });
    response.end(content);
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`JobFit preview running at http://127.0.0.1:${port}`);
});

function proxyApiRequest(clientRequest, clientResponse, requestUrl) {
  const proxyRequest = http.request(
    {
      hostname: apiTarget.hostname,
      port: apiTarget.port || 80,
      method: clientRequest.method,
      path: `${requestUrl.pathname}${requestUrl.search}`,
      headers: {
        ...clientRequest.headers,
        host: apiTarget.host
      }
    },
    (proxyResponse) => {
      clientResponse.writeHead(proxyResponse.statusCode || 502, proxyResponse.headers);
      proxyResponse.pipe(clientResponse);
    }
  );

  proxyRequest.on("error", () => {
    clientResponse.writeHead(502, { "content-type": "application/json; charset=utf-8" });
    clientResponse.end(JSON.stringify({ detail: "Backend API tidak dapat dihubungi." }));
  });

  clientRequest.pipe(proxyRequest);
}
