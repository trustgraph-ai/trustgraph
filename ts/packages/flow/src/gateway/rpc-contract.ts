import { Schema as S } from "effect";
import * as Rpc from "effect/unstable/rpc/Rpc";
import * as RpcGroup from "effect/unstable/rpc/RpcGroup";

export class DispatchPayload extends S.Class<DispatchPayload>("DispatchPayload")({
  scope: S.Literals(["global", "flow"]),
  service: S.String,
  flow: S.optionalKey(S.String),
  request: S.Record(S.String, S.Unknown),
}) {}

export class DispatchStreamChunk extends S.Class<DispatchStreamChunk>("DispatchStreamChunk")({
  response: S.Unknown,
  complete: S.Boolean,
}) {}

export class DispatchError extends S.ErrorClass<DispatchError>("DispatchError")({
  _tag: S.tag("DispatchError"),
  message: S.String,
}) {}

export class Dispatch extends Rpc.make("Dispatch", {
  payload: DispatchPayload,
  success: S.Unknown,
  error: DispatchError,
}) {}

export class DispatchStream extends Rpc.make("DispatchStream", {
  payload: DispatchPayload,
  success: DispatchStreamChunk,
  error: DispatchError,
  stream: true,
}) {}

export const TrustGraphRpcs = RpcGroup.make(Dispatch, DispatchStream);
