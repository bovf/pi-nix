import { Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerTool(defineTool({
    name: "video_model_capabilities",
    label: "Active video review model",
    description: "Read the active Pi session model's declared input capabilities. No credentials, files, provider requests or model changes. Call once before visual review and again after a model switch; do not guess capability from a model name.",
    parameters: Type.Object({}),
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    async execute(_id, _params, _signal, _update, ctx) {
      const model = ctx.model;
      const available = !!model && model.id !== "unknown" && model.provider !== "unknown";
      const result = {
        available,
        provider: available ? model.provider : null,
        id: available ? model.id : null,
        input: available ? [...model.input] : [],
        imageInput: available && model.input.includes("image"),
        evidence: "Active Pi session declaration; not a live provider compatibility test",
        privacy: "Capability is not permission to share footage",
      };
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
    },
  }));
}
