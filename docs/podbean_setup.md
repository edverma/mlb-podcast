# Podbean Setup Guide

This guide will walk you through setting up your Podbean account for the MLB Podcast Distribution system.

## 1. Create a Podbean Account

1. Go to [Podbean's website](https://www.podbean.com/) and sign up for an account.
2. Choose an appropriate plan based on your needs:
   - **Unlimited Audio**: Recommended for regular podcast publishing
   - **Unlimited Plus**: If you need more storage and features
   - **Business**: For enterprise-level needs

## 2. Register OAuth2 Application

1. Log in to your Podbean account.
2. Navigate to the [Podbean Developer Portal](https://developers.podbean.com/).
3. Click on "Create a New App."
4. Fill in the following details:
   - **App Name**: MLB Podcast Distributor
   - **App Description**: Automated MLB podcast distribution system
   - **App Website**: Your website URL
   - **Redirect URI**: Your callback URL (can be set to `http://localhost` for testing)
5. Select the following permissions:
   - `episode_publish` - For creating episodes
   - `episode_update` - For updating episodes
   - `file_media_upload` - For uploading audio files
6. Click "Register" to create your application.
7. You will receive a `client_id` and `client_secret`. Copy these values.

## 3. Configure Environment Variables

1. Add the following to your `.env` file (create it if it doesn't exist):
   ```
   PODBEAN_CLIENT_ID=your_client_id_here
   PODBEAN_CLIENT_SECRET=your_client_secret_here
   ```
2. Replace `your_client_id_here` and `your_client_secret_here` with the values you received.

## 4. Configure Podcast Settings

Log in to your Podbean account and configure the following settings:

### Podcast Information
1. Go to "Settings" > "Basic Information"
2. Set up:
   - Podcast Title: MLB Team Daily Updates (or your preferred name)
   - Description: Daily updates for MLB team performance, news, and analysis
   - Category: Sports & Recreation > Baseball
   - Language: English
   - Keywords: MLB, baseball, sports, daily updates, team name

### Podcast Artwork
1. Go to "Settings" > "Podcast Art"
2. Upload your podcast artwork:
   - Must be 1400x1400 pixels
   - JPG or PNG format
   - Keep file size under 500KB if possible

### Episode Defaults
1. Go to "Settings" > "Episode Defaults"
2. Configure:
   - Default episode settings
   - SEO settings
   - Distribution settings

## 5. Testing Your Configuration

After completing the setup, test your configuration:

1. Run a test upload using our `podbean_distributor.py` utility:
   ```
   python -c "from utils.podbean_distributor import PodbeanDistributor; p = PodbeanDistributor(); p.authenticate()"
   ```
2. If successful, you should see a confirmation message with no errors.

## Troubleshooting

- **Authentication Issues**: Verify your client ID and secret are correct
- **Upload Failures**: Check file size limits and format
- **Publishing Errors**: Ensure all required metadata is provided

## Additional Resources

- [Podbean API Documentation](https://developers.podbean.com/podbean-api-docs/)
- [Podbean Help Center](https://help.podbean.com/) 