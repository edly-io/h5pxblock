
# Play H5P content in Open edX using h5pxblock

H5P Xblock provides ability to host and play H5P content in open edX. It has few more features

1. Ability to mark H5P content complete in open edX
2. Ability to capture score of H5P content in open edX
3. Save learner state which can be retrieved later
4. Ability to host H5P content on cloud storage like AWS S3

# Setup

### Install Xblock

```
pip install h5p-xblock
```

### Update Advanced Settings of course

Update course advanced settings by adding `h5pxblock`

![Update course advanced settings](https://github.com/edly-io/h5pxblock/blob/master/docs/images/course_advance_settings.png?raw=true)

### Upload H5P Content

Xblock should be available in Advanced component list of course unit now. Add xblock in unit and click "Edit" button to  
upload H5P content and configure it.

![Upload and configure H5P content in Studio](https://github.com/edly-io/h5pxblock/blob/master/docs/images/upload_content.png?raw=true)

### Publish Content

Use "Preview" button to preview it or publish your content and use "View Live Version" button to see how it appears  
on LMS

![Preview H5P content in LMS](https://github.com/edly-io/h5pxblock/blob/master/docs/images/preview_content.png?raw=true)


# Working with translations

You can help by translating this project. Follow the steps below:

1. Create a folder for the translations in `locale/`, eg: `locale/es_419/LC_MESSAGES/`, and create your `text.po` file
with all the translations.
2. Run `make compile_translations`, this will generate the `text.mo` file.
3. Create a pull request with your changes.
