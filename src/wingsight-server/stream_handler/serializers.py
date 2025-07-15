import boto3

from rest_framework import serializers

from .models import StreamSubscription, RecognitionEntry


from wingsight.settings import S3_BUCKET_NAME


class StreamSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreamSubscription
        fields = '__all__'


class RecognitionEntrySerializer(serializers.ModelSerializer):
    presigned_thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = RecognitionEntry
        fields = [
            "id",
            "earth_timestamp",
            "stream_timestamp",
            "recognized_specie_name",
            "presigned_thumbnail_url",
        ]

    def get_presigned_thumbnail_url(self, obj):
        if not obj.recognized_specie_img_url:
            return None

        try:
            # Extract bucket and key from URL
            s3_url = obj.recognized_specie_img_url
            key = s3_url.split(f"{S3_BUCKET_NAME}.s3.amazonaws.com/")[-1]

            s3_client = boto3.client('s3')
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET_NAME, 'Key': key
                },
                ExpiresIn=3600  # 1 hour
            )
            return presigned_url

        except Exception as e:
            raise
