import requests

class RestBai:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_endpoint = "https://api-eu.restb.ai/vision/v2/multipredict"
        self.json_response = None
        self.classes = {}

    def response(self, image_url, model_id):
        # create a dictionary with the request parameters
        payload = {
            "client_key": self.api_key,
            "model_id": model_id,
            "image_url": image_url
        }

        # send a GET request to the API endpoint with the request parameters
        response = requests.get(self.api_endpoint, params=payload)

        # parse the JSON response
        self.json_response = response.json()

        # return the labels
        return self.json_response

    def return_classes(self):
        # return the classes
        # {'error': 'false', 'response': {'solutions': {'re_features_v4': {'detections': [{'details': [], 'label': 'tv'}, {'details': [], 'label': 'built_in_shelves'}, {'details': [], 'label': 'beamed_ceiling'}, {'details': [], 'label': 'coffered_ceiling'}, {'details': [], 'label': 'natural_light'}, {'details': [], 'label': 'fireplace'}, {'details': [{'label': 'dark'}], 'label': 'hardwood_floor'}]}}}, 'time': '2023-05-12T23:13:37.276101', 'correlation_id': '5eac8d67-b889-442f-b6ec-19e80520ef6a', 'version': '2'}
        for label in self.json_response["response"]["solutions"][model_id]["detections"]:
            # print(label["label"])
            center = None
            self.classes[label["label"]] = center
        return self.classes
        
            


# Define API key
api_key = "e311a67a878470f221c88835a02a58702f80773dd4d523e308822e94d01a39a0"

# create a RestBai instance with your API key
restbai = RestBai(api_key)

# specify the image URL you want to classify and the model ID to use
image_url = "https://demo.restb.ai/images/demo/demo-1.jpg"
model_id = "re_features_v4"

# classify the image and print the result
result = restbai.response(image_url, model_id)
print(result)

# return the classes
classes = restbai.return_classes()
print(classes)
