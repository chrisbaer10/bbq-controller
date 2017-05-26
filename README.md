# bbq-controller

Installation Instructions:

Use PiBakery to write an SD card with the following startup properties:


set locale

sudo pip install plotly
python -c "import plotly; plotly.tools.set_credentials_file(username='your_username', api_key='your_api_key', stream_ids=['stream1_id','stream2_id'])"

<b>Build Docker Image</b>
<br>
docker build -t bbq ~/bbq-controller --no-cache=true

<b>Run Docker Image</b>
<br>
docker run --device /dev/ttyAMA0:/dev/ttyAMA0 --device /dev/mem:/dev/mem --privileged --env-file ~/bbq-controller/env.list --name bbq -t bbq
