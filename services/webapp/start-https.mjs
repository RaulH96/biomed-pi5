import { createServer } from "https";
import { readFileSync } from "fs";
import { parse } from "url";
import next from "next";

const app = next({ dev: false });
const handle = app.getRequestHandler();

const httpsOptions = {
  key: readFileSync("./192.168.1.75-key.pem"),
  cert: readFileSync("./192.168.1.75.pem"),
};

app.prepare().then(() => {
  createServer(httpsOptions, (req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  }).listen(3000, "0.0.0.0", () => {
    console.log("> Ready on https://192.168.1.75:3000");
  });
});
