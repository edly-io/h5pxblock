
# Play H5P content in Open edX using h5pxblock

H5P Xblock provides ability to host and play H5P content in open edX. It has few more features

1. Ability to mark H5P content complete in open edX
2. Ability to capture score of H5P content in open edX
3. Save learner state which can be retrieved later
4. Ability to host H5P content on cloud storage like AWS S3

## Setup

### Install Xblock

```bash
pip install h5p-xblock
```

or if you're using tutor to manage your organization:

```bash
tutor config save --append OPENEDX_EXTRA_PIP_REQUIREMENTS=h5p-xblock
tutor images build openedx
```

### Update Advanced Settings of course

Update course advanced settings by adding `h5pxblock`

![Update course advanced settings](https://github.com/edly-io/h5pxblock/blob/master/docs/images/course_advance_settings.png?raw=true)

### Upload H5P Content

Xblock should be available in Advanced component list of course unit now. Add xblock in unit and click "Edit" button to upload H5P content and configure it.

![Upload and configure H5P content in Studio](https://github.com/edly-io/h5pxblock/blob/master/docs/images/upload_content.png?raw=true)

### Publish Content

Use "Preview" button to preview it or publish your content and use "View Live Version" button to see how it appears on LMS

![Preview H5P content in LMS](https://github.com/edly-io/h5pxblock/blob/master/docs/images/preview_content.png?raw=true)

### Configuring S3 as a Storage Backend

H5P relies on ``DEFAULT_FILE_STORAGE`` setting to stores h5p content. In case of S3 storage, make sure your platform level S3 storage settings are set appropriately. If you either have set ``AWS_QUERYSTRING_AUTH = True`` then you have to set custom S3 storage settings for H5P xblock since singed url are not supported or if you want to store H5P content in a separate S3 bucket instead of default one you have to set custom S3 storage settings too.

Here is the required configuration:

```python
H5PXBLOCK_STORAGE = {
    "storage_class": "storages.backends.s3boto3.S3Boto3Storage",
    "settings": {
        "bucket_name": "my-s3-public-bucket",
        "querystring_auth": False,
    },
}
```

Please ensure that your bucket is publicly accessible to enable seamless content storage and retrieval via S3.

## Working with translations

You can help by translating this project. Follow the steps below:

1. You need `i18n_tool` to "collect" and "compile" translations. If you already have it, proceed to the next item; otherwise:

```bash
pip install git+https://github.com/openedx/i18n-tools
```

1. Create a folder for the translations in `locale/`, eg: `locale/es_419/LC_MESSAGES/`, and create your `text.po` file
with all the translations.
1. Run `make compile_translations`, this will generate the `text.mo` file.
1. Create a pull request with your changes.
