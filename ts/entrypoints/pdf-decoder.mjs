import("../packages/flow/dist/decoding/pdf-decoder.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
