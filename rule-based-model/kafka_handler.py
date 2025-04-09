from botocore.exceptions import ClientError
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

from ecaption_utils.kafka.faust import get_faust_app, initialize_topics, FaustApplication, get_error_handler
from ecaption_utils.kafka.topics import Topic, get_event_type

from parser import *
from renderer import *
from sample_producer import sample_query_event_long
from util import *
import os
import json
import bisect
import requests

load_dotenv()
broker_url = os.environ.get("KAFKA_BROKER_URL")
port = os.environ.get("INFOGRAPHIC_GENERATION_SERVICE_PORT")
s3_bucket_name = os.environ.get("S3_BUCKET_NAME")
infographic_base_url = os.environ.get("INFOGRAPHIC_BASE_URL")

app = get_faust_app(FaustApplication.InfographicGeneration, broker_url=broker_url, port=port)
topics = initialize_topics(
    app, 
    [
        Topic.INFORMATION_QUERYING_RESULTS, 
        Topic.ADD_INSTRUCTION, 
        Topic.DELETE_INSTRUCTION, 
        Topic.NEW_INFOGRAPHIC, 
        Topic.MODIFIED_INFOGRAPHIC, 
        Topic.MOVE_INSTRUCTION
    ]
)
handle_error = get_error_handler(app)

@app.agent(topics[Topic.INFORMATION_QUERYING_RESULTS])
async def handle_infographic_generation(event_stream):
    async for event in event_stream:
        parsed_data, layout_params = parse_generation_event(event)
        request_id = parsed_data["request_id"]

        infographic_img = render_rule_based_infographic(parsed_data)

        img_bytes = BytesIO()
        infographic_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        json_data = json.dumps(layout_params)
        json_data_bytes = BytesIO(json_data.encode('utf-8'))

        print('Uploading infographic...')
        img_success = upload_fileobj(img_bytes, s3_bucket_name, '{}.jpeg'.format(str(request_id)))
        json_success = upload_fileobj(json_data_bytes, s3_bucket_name, '{}.json'.format(str(request_id)))
        if not (img_success and json_success):
            await handle_error(
                event.request_id,
                error_type=FaustApplication.InfographicGeneration,
                error_message='Error while uploading to S3: ' + str(e)
            )
            continue

        url = infographic_base_url + '/{}.jpeg'.format(str(request_id))
        topic = Topic.NEW_INFOGRAPHIC
        Event = get_event_type(topic)
        event = Event(infographic_link=url, request_id=request_id)
        await topics[topic].send(value=event)

# Testing-------------------------------------------------------
if __name__ == '__main__':
    from unittest.mock import MagicMock, patch
    import asyncio

    # Mock S3 upload function
    def mock_upload_fileobj(file_obj, bucket_name, file_key):
        print(f"Mock upload: {file_key} to bucket: {bucket_name}")
        return True

    class FakeKafkaEventStream:
        async def __aiter__(self):
            yield sample_query_event_long

    @patch("util.upload_fileobj", side_effect=mock_upload_fileobj)
    async def test_handle_infographic_generation(mock_upload):
        event_stream = FakeKafkaEventStream()

        async for event in event_stream:
            parsed_data, layout_params = parse_generation_event(event)
            request_id = parsed_data["request_id"]

            infographic_img = render_rule_based_infographic(parsed_data)
            infographic_img.show()

            img_bytes = BytesIO()
            infographic_img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            json_data = json.dumps(layout_params)
            json_data_bytes = BytesIO(json_data.encode('utf-8'))

            print('Uploading infographic...')
            img_success = mock_upload(img_bytes, 'mock_bucket', '{}.jpeg'.format(str(request_id)))
            json_success = mock_upload(json_data_bytes, 'mock_bucket', '{}.json'.format(str(request_id)))
            
            if not (img_success and json_success):
                print(f"Error uploading to S3: {request_id}")
                return

            url = f"mock_base_url/{request_id}.jpeg"
            print(f"Infographic uploaded to: {url}")

    asyncio.run(test_handle_infographic_generation())
