try {
  (function (require) {
    var config = window.H5PStandaloneConfig || {};
    require.config({
      paths: {
        h5p: config.mainBundleUrl ? config.mainBundleUrl.replace(/\.js$/, "") : "https://cdn.jsdelivr.net/npm/h5p-standalone@3.8.2/dist/main.bundle",
      },
    });
  }).call(this, require || RequireJS.require);
} catch (e) {
  console.log("Unable to load h5p-standalone via requirejs");
}
