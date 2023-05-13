import base64
import datetime
import os
from google.cloud import storage

def save_image_to_gcs(base64_image):

    # Get the current time
    current_time = datetime.datetime.now().time()

    # Format the time as HH:MM:SS
    time_string = current_time.strftime("%H_%M_%S")

    print("Current time string:", time_string)

    # Decode the base64 image
    image_data = base64.b64decode(base64_image)

    # Set up Google Cloud Storage client
    json_key_path = 'keys.json'  # Path to your JSON key file
    storage_client = storage.Client.from_service_account_json(json_key_path)


    # Set the bucket and filename for the image
    bucket_name = 'restbaitempo'
    filename = time_string+".png"

    # Upload the image to the specified bucket
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_data, content_type='image/png')

    # Generate the public URL for the image
    url = f'https://storage.googleapis.com/{bucket_name}/{filename}'

    return url, 640, 480

sample_base64_image = ""

if __name__ == "__main__":
    # Sample base64 image
        # Call the function to save the image to GCS
    
    image_url = save_image_to_gcs(sample_base64_image)

    # Print the URL of the uploaded image
    print("Image uploaded successfully. URL:", image_url)
