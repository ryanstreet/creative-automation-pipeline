# Adobe Creative Automation Pipeline

This project provides a unified command-line interface for Adobe creative automation workflows, including AI image generation, Photoshop document manipulation, and Amazon S3 file management.

## Quick Start

Use the unified command interface:

```bash
# Generate Adobe Firefly prompts from campaign briefs
python cap.py campaign-prompt tmp/campaign_brief.json

# Generate images using Adobe Firefly API
python cap.py firefly-image "a beautiful sunset over mountains"

# Retrieve Photoshop document manifests
python cap.py photoshop-manifest https://example.com/file.psd

# List available manifest files in tmp directory
python cap.py photoshop-manifest --list-manifests

# List layers from existing local manifest file
python cap.py photoshop-manifest --list-layers tmp/document_manifest.json
python cap.py photoshop-manifest --list-layers document_manifest.json  # auto-searches tmp/

# Replace smart objects in PSD files
python cap.py smart-object --manifest manifest.json --layer "Logo" --smart-object-url url --output-url url

# Edit text layers in PSD files
python cap.py text-layer --input-url url --layer "Title" --text "New Text" --output-url url

# Create PNG renditions from PSD files
python cap.py rendition --input-url url --output-url url

# Manage S3 file operations
python cap.py s3 upload file.txt bucket key
python cap.py s3 download bucket key
python cap.py s3 presigned-upload bucket key

# Monitor rate limiting status
python cap.py rate-limit
python cap.py rate-limit --detailed
python cap.py rate-limit --json

# Execute complete campaign automation pipeline
python cap.py campaign-pipeline --bucket my-s3-bucket
python cap.py campaign-pipeline tmp/briefs/campaign_brief.json --bucket my-s3-bucket
python cap.py campaign-pipeline --bucket my-s3-bucket --skip-firefly
```

For detailed help on any command:
```bash
python cap.py --help
python cap.py <command> --help
```

## Available Commands

### Campaign Prompt Generator
Generates Adobe Firefly prompts from campaign brief JSON files using OpenAI's API. Extracts target demographics and psychographics to create contextual background image prompts.

### Firefly Image Generator
Generates AI images using Adobe Firefly API V3 Async. Supports multiple variations, custom dimensions, and different content classes.

### Photoshop Document Manifest
Retrieves document manifests from Adobe Photoshop API asynchronously and saves output to JSON files. Also provides functionality to list available manifest files in the tmp directory and extract layer information from existing local manifest files.

### Smart Object Replacer
Replaces smart objects in PSD files using Adobe Firefly Services Photoshop API. Takes a document manifest JSON file, locates a specified layer, and replaces it with a new smart object from an S3 URL.

### Text Layer Editor
Edits text layers in PSD files using Adobe Firefly Services Photoshop API. Takes a layer name and replacement text, then updates the text content of that layer.

### PSD Rendition Creator
Creates PNG renditions of PSD files using Adobe Photoshop API createRenditionAsync endpoint. Takes AWS presigned URLs for input PSD and output PNG files.

### S3 Manager
Comprehensive tool for uploading and downloading files to/from Amazon S3, including presigned URL generation for secure file sharing.

### Rate Limiting Status
Displays real-time status and configuration of the built-in API rate limiting system. Provides monitoring capabilities for all API operations.

## Prerequisites

1. **Adobe Developer Console Account**: Create an application in the Adobe Developer Console to get your API credentials for Photoshop and Firefly operations.

2. **AWS Account**: AWS account with S3 access for file management operations.

3. **Python 3.7+**: All operations require Python 3.7 or higher.

4. **Dependencies**: Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Rate Limiting

The Creative Automation Pipeline includes a comprehensive rate limiting system to prevent API abuse and ensure reliable service. All API operations are automatically rate-limited.

### Rate Limiting Commands

```bash
# Basic rate limit status
python cap.py rate-limit

# Detailed configuration information
python cap.py rate-limit --detailed

# JSON output for automation/monitoring
python cap.py rate-limit --json
```

For detailed information about the rate limiting system, configuration options, and implementation details, see [RATE_LIMITING.md](RATE_LIMITING.md).

## Setup

### Adobe API Credentials

1. **Get Adobe API Credentials**:
   - Go to [Adobe Developer Console](https://developer.adobe.com/console/)
   - Create a new project or use an existing one
   - Add the Photoshop API and Firefly API to your project
   - Note down your `Client ID` and `Client Secret`

2. **Set Environment Variables**:
   ```bash
   export CLIENT_ID='your_client_id_here'
   export CLIENT_SECRET='your_client_secret_here'
   ```

### AWS Credentials

1. **Configure AWS Credentials** (choose one method):
   
   **Method A: AWS CLI (Recommended)**
   ```bash
   aws configure
   ```
   
   **Method B: Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID='your_access_key_here'
   export AWS_SECRET_ACCESS_KEY='your_secret_key_here'
   export AWS_DEFAULT_REGION='us-east-1'
   ```
   
   **Method C: Credentials File**
   ```bash
   mkdir -p ~/.aws
   cat > ~/.aws/credentials << EOF
   [default]
   aws_access_key_id = your_access_key_here
   aws_secret_access_key = your_secret_key_here
   EOF
   ```

2. **Test AWS Setup**:
   ```bash
   aws s3 ls
   ```

### OpenAI API Key (for Campaign Prompt Generator)

Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Command Reference

All commands support the `--help` flag for detailed usage information:

```bash
python cap.py <command> --help
```

### Common Options

Most commands support these common options:
- `--debug`: Enable debug output with detailed API responses
- `--poll-interval`: Polling interval in seconds (default: 5)
- `--max-attempts`: Maximum polling attempts before timeout (default: 120)

### Interactive Mode

All commands support interactive mode when required arguments are not provided. Simply run the command without arguments to enter interactive mode.

## How It Works

The Creative Automation Pipeline provides a unified interface to Adobe's creative APIs:

1. **Authentication**: All Adobe operations authenticate using your Developer Console credentials
2. **Asynchronous Processing**: Most operations use Adobe's async APIs with status polling
3. **Rate Limiting**: Built-in rate limiting prevents API abuse and ensures reliable service
4. **Error Handling**: Comprehensive error handling with helpful messages and recovery options
5. **Interactive Mode**: All commands support interactive mode for user-friendly operation

## Error Handling

All commands include comprehensive error handling for:
- Invalid URLs and file paths
- Authentication failures
- API request errors and rate limiting
- Job failures and timeouts
- File I/O errors
- Network connectivity issues
- AWS credential and permission issues

## Campaign Pipeline Command

The `campaign-pipeline` command executes a complete automation workflow that combines all available functionality into a single streamlined process. This command is designed to process campaign briefs and automatically generate all required creative assets.

### What the Campaign Pipeline Does

1. **Parse Campaign Briefs**: Loads and validates campaign brief JSON files from `tmp/briefs/` directory
2. **Upload Templates**: Uploads PSD templates to S3 and generates presigned download URLs
3. **Create Document Manifests**: Uses Adobe Photoshop API to analyze template structure
4. **Apply Text Edits**: Updates "Campaign Message" layer with text from campaign brief
5. **Replace Product Images**: Uploads product photos and replaces "Product" layer via smart object replacement
6. **Generate Background Images**: Uses Firefly API with AI-generated prompts based on campaign demographics
7. **Create Final Variations**: Replaces "Background Image" layer with generated Firefly images
8. **Generate Renditions**: Creates PNG renditions of all final PSD files
9. **Organize Output**: Downloads renditions to organized folders by aspect ratio

### Campaign Brief Structure

The pipeline expects campaign brief JSON files with the following structure:

```json
{
  "campaign_message": "Your campaign message text",
  "technical_specs": {
    "template": "template-name.psd",
    "aspect_ratio": "1x1",
    "asset_width": 2048,
    "asset_height": 2048,
    "variations": 3,
    "product_photo": "product-image.png"
  },
  "target_audience": {
    "demographics": {
      "age_range": "25-45",
      "income_level": "Middle to High",
      "profession": ["Professionals", "Entrepreneurs"]
    },
    "psychographics": {
      "interests": ["technology", "lifestyle"],
      "values": ["innovation", "quality"],
      "behaviors": ["online shopping", "social media"]
    }
  }
}
```

### Required Directory Structure

```
tmp/
├── briefs/           # Campaign brief JSON files
├── templates/        # PSD template files
├── images/           # Product image files
├── manifests/        # Generated document manifests
└── output/           # Final rendered assets
    └── {aspect_ratio}/  # Organized by aspect ratio
```

### Usage Examples

```bash
# Process all briefs in tmp/briefs/ directory
python cap.py campaign-pipeline --bucket my-creative-bucket

# Process specific brief file
python cap.py campaign-pipeline tmp/briefs/luxury-watch-campaign.json --bucket my-bucket

# Process multiple briefs
python cap.py campaign-pipeline brief1.json brief2.json --bucket my-bucket

# Skip Firefly image generation (faster, uses original backgrounds)
python cap.py campaign-pipeline --bucket my-bucket --skip-firefly

# Use different AWS region
python cap.py campaign-pipeline --bucket my-bucket --region us-west-2

# Enable debug output for troubleshooting
python cap.py campaign-pipeline --bucket my-bucket --debug
```

### Output Files Generated

For each campaign brief, the pipeline creates:

1. **Text-Edited Template**: `{template-name}-text.psd`
2. **Product-Replaced Template**: `{template-name}-product.psd`
3. **Final Variations**: `{template-name}-final-{1-N}.psd` (one per Firefly variation)
4. **Rendered PNGs**: `{template-name}-final-{1-N}.png` in `tmp/output/{aspect_ratio}/`

### Interactive Mode

If you run the command without required parameters, it will start interactive mode:

```bash
python cap.py campaign-pipeline
```

This will guide you through:
- Selecting campaign brief files
- Entering S3 bucket name
- Configuring AWS region
- Setting polling intervals
- Enabling debug mode
- Choosing whether to skip Firefly generation

### Prerequisites

- Adobe Developer Console credentials (CLIENT_ID, CLIENT_SECRET)
- OpenAI API key for prompt generation
- AWS credentials with S3 access
- Campaign brief JSON files in `tmp/briefs/`
- PSD template files in `tmp/templates/` or `tmp/`
- Product image files in `tmp/images/` or `tmp/`

### Error Handling

The pipeline includes comprehensive error handling:
- Continues processing other briefs if one fails
- Provides detailed logging of each step
- Gracefully handles missing files or API errors
- Creates organized output directories automatically

## Troubleshooting

### Adobe API Issues
1. **Authentication Issues**: Ensure your `CLIENT_ID` and `CLIENT_SECRET` are correct and properly exported
2. **File Access**: Make sure the PSD file URL is publicly accessible
3. **API Rate Limits**: All APIs have rate limits - use debug mode to see detailed error responses
4. **Firefly API Issues**: If image generation fails, check that your Adobe account has Firefly access enabled
5. **Smart Object Issues**: Ensure the manifest file is valid and contains the specified layer
6. **Layer Not Found**: Verify the layer name exists in the manifest - use debug mode to see available layers
7. **Rendition Issues**: Ensure both input PSD and output PNG URLs are valid AWS presigned URLs with proper permissions

### Rate Limiting Issues
1. **Rate Limit Exceeded**: Use `python cap.py rate-limit` to check current status and wait times
2. **Slow Performance**: Rate limiting may cause delays - this is normal behavior to prevent API abuse
3. **Configuration Issues**: Verify environment variables are set correctly for rate limiting
4. **Disable Rate Limiting**: Set `ENABLE_RATE_LIMITING=false` for testing (not recommended for production)
5. **Custom Limits**: Adjust rate limits via environment variables based on your API quotas
6. **Monitoring**: Use `python cap.py rate-limit --json` for automated monitoring systems

For detailed rate limiting configuration and troubleshooting, see [RATE_LIMITING.md](RATE_LIMITING.md).

### AWS S3 Issues
1. **AWS Credentials**: Ensure your AWS credentials are valid and have S3 permissions
2. **Bucket Access**: Verify the bucket exists and you have read/write permissions
3. **Region Mismatch**: Make sure you're using the correct AWS region for your bucket
4. **Network Issues**: Check your internet connection and firewall settings

### General Issues
1. **Permissions**: Ensure you have write permissions to the output directory
2. **Network Issues**: Check your internet connection and firewall settings
3. **Python Dependencies**: Make sure all required packages are installed with `pip install -r requirements.txt`

## API Documentation

### Amazon S3 API
- [Amazon S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Boto3 S3 Client Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)

### Adobe Photoshop API
- [Adobe Photoshop API Documentation](https://developer.adobe.com/firefly-services/docs/photoshop/api/)
- [getDocumentManifestAsync](https://developer.adobe.com/firefly-services/docs/photoshop/api/#operation/getDocumentManifestAsync)
- [replaceSmartObjectAsync](https://developer.adobe.com/firefly-services/docs/photoshop/api/#operation/replaceSmartObjectAsync)
- [createRenditionAsync](https://developer.adobe.com/firefly-services/docs/photoshop/api/#operation/createRenditionAsync)
- [facadeJobStatus](https://developer.adobe.com/firefly-services/docs/photoshop/api/#operation/facadeJobStatus)

### Adobe Firefly API
- [Adobe Firefly API Documentation](https://developer.adobe.com/firefly-services/docs/firefly-api/)
- [Firefly API V3 Async Image Generation](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/api/image_generation/V3_Async/)
- [Using Firefly Asynchronous APIs](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/using-async-apis/)
