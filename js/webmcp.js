// WebMCP integration for agent discoverability
if (typeof navigator !== 'undefined' && navigator.modelContext && typeof navigator.modelContext.registerTool === 'function') {
  navigator.modelContext.registerTool({
    name: "read_content",
    description: "Read site content",
    inputSchema: { type: "object", properties: { page: { type: "string" } } },
    execute: (args) => { 
      return { result: "This is a static site. Navigate to the requested URL to read content." }; 
    }
  });
}
