const { defineConfig } = require("cypress");

module.exports = defineConfig({
  projectId: 'h5pxblock_cypress',
  e2e: {
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    env: {
      STUDIO_URL: "http://localhost:8000/scenario/h5pxblock.0/studio_view/",
      LMS_URL: "http://localhost:8000/scenario/h5pxblock.0/"
    }
  },
});
