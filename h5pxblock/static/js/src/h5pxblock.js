/* Javascript for H5PPlayerXBlock. */
function H5PPlayerXBlock(runtime, element, args) {
  function initH5P(H5PStandalone, service) {
    if (!window.H5PPlayerXBlockPromises) {
      window.H5PPlayerXBlockPromises = [];
    }
    const contentUserDataUrl = runtime.handlerUrl(
      element,
      "user_interaction_data"
    );
    const contentxResultSaveUrl = runtime.handlerUrl(element, "result_handler");

    const playerPromise = async function edXH5PPlayer(el) {
      if (el && $(el).children(".h5p-iframe-wrapper").length == 0) {
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
          await new H5PStandalone.H5P(el, options);
          $(el).siblings(".spinner-container").find(".spinner-border").hide();
          $(el).show();

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
    };

    const h5pel = document.getElementById("h5p-" + args.player_id);
    window.H5PPlayerXBlockPromises.push(playerPromise(h5pel));
    window.H5PXBlockPlayersInitlized = false;

    $(function ($) {
      if (!H5PXBlockPlayersInitlized) {
        window.H5PXBlockPlayersInitlized = true;
        Promise.all(window.H5PPlayerXBlockPromises).then((_) => {});
      } 
    });
  }

  if (typeof require === "function") {
    require(["h5p"], function (H5PStandalone) {
      initH5P(H5PStandalone, "cms");
    });
  } else {
    loadJS(function () {
      initH5P(window.H5PStandalone, "lms");
    });
  }
}

function loadJS(callback) {
  if (window.H5PStandalone) {
    callback();
  } else {
    // Load jsMind dynamically using $.getScript
    $.getScript(
      "https://cdn.jsdelivr.net/npm/h5p-standalone@3.7.0/dist/main.bundle.js"
    )
      .done(function () {
        window.H5PStandalone = H5PStandalone;
        callback();
      })
      .fail(function () {
        console.error("Error loading H5PStandalone.");
      });
  }
}
