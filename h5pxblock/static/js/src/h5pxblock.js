/* Javascript for H5PPlayerXBlock. */
function H5PPlayerXBlock(runtime, element, args) {

    if (!window.H5PPlayerXBlockPromises) {
        window.H5PPlayerXBlockPromises = [];
    }
    const contentUserDataUrl = runtime.handlerUrl(element, 'user_interaction_data');
    const contentFinishUrl = runtime.handlerUrl(element, 'finish_handler');

    const playerPromise = function edXH5PPlayer(el) {
        const userObj = { 'name': args.user_full_name, 'mail': args.user_email };
        const options = {
            h5pJsonPath: args.h5pJsonPath,
            frameJs: 'https://cdn.jsdelivr.net/npm/h5p-standalone@3.5.1/dist/frame.bundle.js',
            frameCss: 'https://cdn.jsdelivr.net/npm/h5p-standalone@3.5.1/dist/styles/h5p.css',
            user: userObj,
            saveFreq: 15,
            customJs: args.customJsPath,
            contentUserData: [{
                state: args.userData
            }],
            postUserStatistics: true,
            ajax: { 
                contentUserDataUrl: contentUserDataUrl,
                setFinishedUrl: contentFinishUrl 
            } //TODO set appropriate handlers

        }
        return new H5PStandalone.H5P(el, options);
    };

    const h5pel = document.getElementById('h5p-' + args.player_id);
    window.H5PPlayerXBlockPromises.push(h5pel);
    window.H5PXBlockPlayersInitlized = false;

    $(function ($) {
        if (!H5PXBlockPlayersInitlized) {
            window.H5PXBlockPlayersInitlized = true;
            window.H5PPlayerXBlockPromises.reduce(
                (p, x) =>
                    p.then(_ => playerPromise(x)),
                Promise.resolve()
            )
            H5P.externalDispatcher.on("xAPI", (event) => {
                //TODO do something useful with the event
                console.log("xAPI event: ", event);
            });
        }
    });

    var handlerUrl = runtime.handlerUrl(element, 'studio_submit');

    $(element).find('.save-button').bind('click', function() {
        var form_data = new FormData();
        var file_data = $(element).find('#h5p_file').prop('files')[0];

        form_data.append('file', file_data);
        console.log(file_data)

        $.ajax({
          url: handlerUrl,
          dataType: 'text',
          cache: false,
          contentType: false,
          processData: false,
          data: form_data,
          type: "POST",
          success: function(response){

          }
        });

      });

    $(element).find('.cancel-button').bind('click', function() {

    });
}
