import { connect } from "nats";

async function main() {
  const nc = await connect({ servers: "nats://localhost:4222" });
  const jsm = await nc.jetstreamManager();

  try {
    const info = await jsm.streams.info("tg_flow");
    console.log("Current stream subjects:", info.config.subjects);
    await jsm.streams.delete("tg_flow");
    console.log("Deleted tg_flow stream");
  } catch (e) {
    console.log("No stream to delete:", (e as Error).message);
  }

  await nc.close();
}

main();
