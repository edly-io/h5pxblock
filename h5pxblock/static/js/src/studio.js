function H5PStudioXBlock(runtime, element) {

    var handlerUrl = runtime.handlerUrl(element, 'studio_submit');

    function setProgressBarWidth(width){
        $('.xb-h5p-progress-bar .progress-bar', $(element))
            .prop('aria-valuenow', width)
            .css({
                width: width + '%'
            })
            .text(width + '%');
    }

    $(element).find('.save-button').bind('click', function () {
        var form_data = new FormData();
        var h5p_content_bundle = $(element).find('#xb_h5p_file').prop('files')[0];
        var display_name = $(element).find('input[name=xb_display_name]').val();
        var show_frame = $(element).find('#xb_field_edit_show_frame').val();
        var show_copyright = $(element).find('#xb_field_edit_show_copyright').val();
        var show_h5p = $(element).find('#xb_field_edit_show_h5p').val();
        var show_fullscreen = $(element).find('#xb_field_edit_show_fullscreen').val();
        var is_scorable = $(element).find('#xb_field_edit_is_scorable').val();
        var save_freq = $(element).find('#xb_field_edit_save_freq').val();

        form_data.append('h5p_content_bundle', h5p_content_bundle);
        form_data.append('display_name', display_name);
        form_data.append('show_frame', show_frame);
        form_data.append('show_copyright', show_copyright);
        form_data.append('show_h5p', show_h5p);
        form_data.append('show_fullscreen', show_fullscreen);
        form_data.append('is_scorable', is_scorable);
        form_data.append('save_freq', save_freq);

        if (runtime.hasOwnProperty('notify')) { //xblock workbench runtime does not have `notify` method
            runtime.notify('save', { state: 'start' });
        }        

        $.ajax({
            url: handlerUrl,
            dataType: 'text',
            cache: false,
            contentType: false,
            processData: false,
            data: form_data,
            type: "POST",
            xhr: function () {
                if(h5p_content_bundle !== undefined) {
                    $('.progress-bar-container').show();
                }
                else {
                    $('.progress-bar-container').hide();
                }
                var xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener("progress", function (evt) {
                    if (evt.lengthComputable) {
                        var percentComplete = evt.loaded / evt.total;
                        console.log(percentComplete);
                        var width = percentComplete * 100;
                        setProgressBarWidth(width);
                    }
                }, false);
                return xhr;
            },

            success: function (response) {
                if (runtime.hasOwnProperty('notify')) { //xblock workbench runtime does not have `notify` method
                    runtime.notify('save', { state: 'end' });
                }
            }
        });

    });

    $(element).find('.cancel-button').bind('click', function () {
        if (runtime.hasOwnProperty('notify')) { //xblock workbench runtime does not have `notify` method
            runtime.notify('cancel', {});
        }
    });

}

