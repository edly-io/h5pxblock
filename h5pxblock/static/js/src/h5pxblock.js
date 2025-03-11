/* Javascript for H5PPlayerXBlock. */
function H5PPlayerXBlock(runtime, element, args) {
  // Initialize queue if not exists
  if (!window.H5PBlocksQueue) {
    window.H5PBlocksQueue = [];
    window.H5PBlocksQueueProcessing = false;
  }
  
  window.H5PBlocksQueue.push({runtime, element, args});
  
  if (!window.H5PBlocksQueueProcessing) {
    processNextBlock();
  }
  
  // Process blocks one at a time
  async function processNextBlock() {
    window.H5PBlocksQueueProcessing = true;
    
    if (window.H5PBlocksQueue.length > 0) {
      const blockData = window.H5PBlocksQueue.shift();
      await initH5PBlock(blockData.runtime, blockData.element, blockData.args);
      processNextBlock();
    } else {
      window.H5PBlocksQueueProcessing = false;
    }
  }
  
  async function initH5PBlock(runtime, element, args) {
    if (typeof require === "function") {
      return new Promise((resolve) => {
        require(["h5p"], function (H5PStandalone) {
          initWithH5P(H5PStandalone, "cms", runtime, element, args)
            .then(resolve);
        });
      });
    } else {
      await loadJS();
      return initWithH5P(window.H5PStandalone, "lms", runtime, element, args);
    }
  }
  
  async function initWithH5P(H5PStandalone, service, runtime, element, args) {
    const contentUserDataUrl = runtime.handlerUrl(
      element,
      "user_interaction_data"
    );
    const contentxResultSaveUrl = runtime.handlerUrl(element, "result_handler");

    const h5pel = document.getElementById("h5p-" + args.player_id);
    if (h5pel && $(h5pel).children(".h5p-iframe-wrapper").length == 0) {
      const userObj = { name: args.user_full_name, mail: args.user_email };
      const options = {
        h5pJsonPath: args.h5pJsonPath,
        frameJs:
          "https://cdn.jsdelivr.net/npm/h5p-standalone@3.7.0/dist/frame.bundle.js",
        frameCss:
          "https://cdn.jsdelivr.net/npm/h5p-standalone@3.7.0/dist/styles/h5p.css",
        frame: args.frame,
        copyright: args.copyright,
        icon: args.icon,
        fullScreen: args.fullScreen,
        user: userObj,
        saveFreq: args.saveFreq,
        customJs: args.customJsPath,
        contentUserData: [
          {
            state: args.userData,
          },
        ],
        ajax: {
          contentUserDataUrl: contentUserDataUrl,
        },
      };

      try {
        await new H5PStandalone.H5P(h5pel, options);
        $(h5pel).siblings(".spinner-container").find(".spinner-border").hide();
        $(h5pel).show();

        H5P.externalDispatcher.on("xAPI", (event) => {
          let hasStatement = event && event.data && event.data.statement;
          if (!hasStatement) {
            return;
          }

          let statement = event.data.statement;
          let validVerb =
            statement.verb &&
            statement.verb.display &&
            statement.verb.display["en-US"];
          if (!validVerb) {
            return;
          }

          let isCompleted =
            statement.verb.display["en-US"] === "answered" ||
            statement.verb.display["en-US"] === "completed" ||
            statement.verb.display["en-US"] === "consumed";
          let isChild =
            statement.context &&
            statement.context.contextActivities &&
            statement.context.contextActivities.parent &&
            statement.context.contextActivities.parent[0] &&
            statement.context.contextActivities.parent[0].id;

          // Store only completed root events.
          if (isCompleted && !isChild) {
            $.ajax({
              type: "POST",
              url: contentxResultSaveUrl,
              data: JSON.stringify(event.data.statement),
            })
            .done(function () {
                  // handle fine request  here
            })
            .fail(function () {
              // handle fails request here
            });
          }
        });

        return Promise.resolve("Result successfully");
      } catch (error) {
        return Promise.reject(error.message);
      }
    }
  }
}

function loadJS() {
  return new Promise((resolve) => {
    if (window.H5PStandalone) {
      resolve();
    } else {
      // Load H5PStandalone dynamically using $.getScript
      $.getScript(
        "https://cdn.jsdelivr.net/npm/h5p-standalone@3.7.0/dist/main.bundle.js"
      )
        .done(function () {
          window.H5PStandalone = H5PStandalone;
          resolve();
        })
        .fail(function () {
          console.error("Error loading H5PStandalone.");
        });
    }
  });
}
