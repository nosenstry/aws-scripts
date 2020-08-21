import boto3
import botocore
import sys
import random
import time


def main():
    AWS_ACCESS = 'AKIASSDYUGRLS5LX5NVO'
    AWS_SECRET = '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'

    ENGINE_NAME = 'mysql'
    ENGINE_VERSION = '5.7.00'
    DB_INSTANCE_TYPE = 'm1.small'
    DB_NAME = 'mysql_db'
    DB_USER_NAME = 'db_user1'
    DB_USER_PASSWORD = 'db_pass123'

    run_index = '%03x' % random.randrange(2**12)

    print ("Disabling warning for Insecure connection")
    botocore.vendored.requests.packages.urllib3.disable_warnings(
        botocore.vendored.requests.packages.urllib3.exceptions.InsecureRequestWarning)

    rds_client = boto3.client(service_name="rds", region_name="symphony",
                              endpoint_url="https://%s/api/v2/aws/rds" % CLUSTER_IP,
                              verify=False,
                              aws_access_key_id=AWS_ACCESS,
                              aws_secret_access_key=AWS_SECRET)

    describe_eng_ver_response = rds_client.describe_db_engine_versions()

    if describe_eng_ver_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        eng_list = [engine for engine in describe_eng_ver_response['DBEngineVersions']
                    if engine['Engine'] == ENGINE_NAME and engine['EngineVersion'] == ENGINE_VERSION]
        assert len(eng_list) == 1, 'Cannot find engine'
        db_param_grp_family = eng_list[0]['DBParameterGroupFamily']
        print("Successfully described DB Engine Versions")
    else:
        print("Couldn't describe DB Engine Versions")

    db_param_grp_name = 'test_param_grp_%s' % run_index
    create_db_params_response = rds_client.create_db_parameter_group(DBParameterGroupName=db_param_grp_name,
                                                                     DBParameterGroupFamily=db_param_grp_family,
                                                                     Description='Test DB Params Group %s' % run_index)

    if create_db_params_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully created DB parameters group %s" % db_param_grp_name)
    else:
        print("Couldn't create DB parameters group")

    def _get_db_param_value(param_group_name, param_name):
        rsp = rds_client.describe_db_parameters(DBParameterGroupName=param_group_name)
        print "In group %s value of %s is %s" % (param_group_name, param_name,
                                                 [param for param in rsp['Parameters']
                                                  if param['ParameterName'] == param_name][0][
                                                  'ParameterValue'])

    _get_db_param_value(db_param_grp_name, 'auto_increment_increment')

    modify_db_params_response = rds_client.modify_db_parameter_group(DBParameterGroupName=db_param_grp_name,
                                                                     Parameters=[{"ParameterName": "autocommit",
                                                                                  "ParameterValue": "false"},
                                                                                 {"ParameterName": "auto_increment_increment",
                                                                                  "ParameterValue": "3"}])

    if modify_db_params_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully modify DB parameters group %s" % db_param_grp_name)
    else:
        print("Couldn't modify DB parameters group")

    _get_db_param_value(db_param_grp_name, 'auto_increment_increment')

    reset_db_params_response = rds_client.reset_db_parameter_group(DBParameterGroupName=db_param_grp_name,
                                                                   ResetAllParameters=True)

    if reset_db_params_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully reset DB parameters group %s" % db_param_grp_name)
    else:
        print("Couldn't reset DB parameters group")

    _get_db_param_value(db_param_grp_name, 'auto_increment_increment')

    db_instance_name = 'test_instance_db_%s' % run_index
    create_db_instance_response = rds_client.create_db_instance(
                                        DBInstanceIdentifier=db_instance_name,
                                        DBInstanceClass=DB_INSTANCE_TYPE,
                                        DBName=DB_NAME,
                                        Engine=ENGINE_NAME,
                                        EngineVersion=ENGINE_VERSION,
                                        MasterUsername=DB_USER_NAME,
                                        MasterUserPassword=DB_USER_PASSWORD,
                                        DBParameterGroupName=db_param_grp_name)

    if create_db_instance_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully create DB instance %s" % db_instance_name)
    else:
        print("Couldn't create DB instance")

    print("waiting for db instance %s to become ready" % db_instance_name)
    number_of_retries = 20
    db_success = False
    for i in xrange(number_of_retries):
        time.sleep(30)
        db_status = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_name)['DBInstances'][0]['DBInstanceStatus']
        if db_status == 'available':
            db_success = True
            print("DB instance %s is ready" % db_instance_name)
            break
        else:
            print("DB instance %s is initializing. Attempt %s" % (db_instance_name, i))

    assert db_success, "DB failed %s to initialize" % db_instance_name

    db_snapshot_name = 'test_snapshot_db_%s' % run_index
    create_db_snapshot_response = rds_client.create_db_snapshot(
                                        DBInstanceIdentifier=db_instance_name,
                                        DBSnapshotIdentifier=db_snapshot_name)

    if create_db_snapshot_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully created DB snapshot %s" % db_instance_name)
    else:
        print("Couldn't create DB snapshot")

    print("waiting for db snapshot %s to become ready" % db_instance_name)
    number_of_retries = 20
    snapshot_success = False
    for i in xrange(number_of_retries):
        time.sleep(30)
        snp_status = rds_client.describe_db_snapshots(DBSnapshotIdentifier=db_snapshot_name)['DBSnapshots'][0]['Status']
        if snp_status == 'available':
            snapshot_success = True
            print("DB snapshot %s is ready" % db_snapshot_name)
            break
        else:
            print("DB snapshot %s is initializing. Attempt %s" % (db_snapshot_name, i))

    assert snapshot_success, "DB failed %s to initialize" % db_snapshot_name

    db_restored_name = 'test_restored_snapshot_db_%s' % run_index
    restore_db_response = rds_client.restore_db_instance_from_db_snapshot(
                                                DBInstanceIdentifier=db_restored_name,
                                                DBSnapshotIdentifier=db_snapshot_name
                                            )

    # check restore DB instance returned successfully
    if restore_db_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully restored DB snapshot %s to instance %s" % (db_snapshot_name, db_restored_name))
    else:
        print("Couldn't restore DB snapshot")

    print("waiting for restored db %s to become ready" % db_instance_name)
    number_of_retries = 20
    restore_success = False
    for i in xrange(number_of_retries):
        time.sleep(30)
        restored_status = rds_client.describe_db_instances(DBInstanceIdentifier=db_restored_name)['DBInstances'][0]['DBInstanceStatus']
        if restored_status == 'available':
            restore_success = True
            print("Restored DB %s is ready" % db_restored_name)
            break
        else:
            print("Restored DB %s is initializing. Attempt %s" % (db_restored_name, i))

    assert restore_success, "Restored DB %s to initialize" % db_restored_name

    # Delete restored DB
    del_restore_db_response = rds_client.delete_db_instance(
                                                DBInstanceIdentifier=db_restored_name,
                                            )

    if del_restore_db_response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print("Successfully sent command to restore DB instance %s" % db_restored_name)
    else:
        print("Couldn't delete restored DB")

    print("waiting for restored db %s to be removed " % db_restored_name)
    number_of_retries = 20
    restore_success = False
    for i in xrange(number_of_retries):
        time.sleep(10)
        try:
            rds_client.describe_db_instances(DBInstanceIdentifier=db_restored_name)
            print("Restored DB still deleting %s is initializing. Attempt %s" % (db_restored_name, i))
        except rds_client.exceptions.DBInstanceNotFoundFault:
            restore_success = True
            print("Restored DB %s is deleted" % db_restored_name)
            break

    assert restore_success, "Restored DB %s to initialize" % db_restored_name

if __name__ == '__main__':
    sys.exit(main()) 
