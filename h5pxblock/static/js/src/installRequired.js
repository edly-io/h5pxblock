try {
  (function (require) {
    require.config({
      paths: {
        h5p: `${window.H5P_STANDALONE_BASE_URL}/main.bundle`,
      },
    });
  }).call(this, require || RequireJS.require);
} catch (e) {
  console.log("Unable to load h5p-standalone via requirejs");
}
