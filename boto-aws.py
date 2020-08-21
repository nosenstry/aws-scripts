import boto3
import sys


def main():
    client = boto3.Session.client(boto3.session.Session(), service_name="ec2", region_name="symphony",
                                  endpoint_url="https://<cluster ip>/api/v2/ec2/",
                                  verify=False,
                                  aws_access_key_id="AKIASSDYUGRLS5LX5NVO",
                                  aws_secret_access_key="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")

    images = client.describe_images()
    image_id = next(image['ImageId'] for image in images if 'centos' in image['Name'])

    print "Found desired image with ID: " + image_id

    ec2_instance = client.run_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1
    )

    if ec2_instance['ResponseMetadata']['HTTPStatusCode'] == 200:
        print "Successfully created instance! " + ec2_instance['Instances'][0]['InstanceId']

    ebs_vol = client.create_volume(
        Size=20,
        AvailabilityZone='symphony'
    )

    volume_id = ebs_vol['VolumeId']

    if ebs_vol['ResponseMetadata']['HTTPStatusCode'] == 200:
        print "Successfully created Volume! " + volume_id

    attach_resp = client.attach_volume(
        VolumeId=volume_id,
        InstanceId=ec2_instance['Instances'][0]['InstanceId'],
        Device='/dev/sdm'
    )

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:])) 
