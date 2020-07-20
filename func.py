import io, json, oci, random, string
from datetime import datetime
from random import randint
from oci.identity.models import CreatePolicyDetails
from oci.object_storage.models import CreateBucketDetails
from oci.limits import QuotasClient
from oci.limits.models import CreateQuotaDetails, UpdateQuotaDetails
from fdk import response

compartment_id = 'ocid1.tenancy.oc1..aaaaaaaaqqzek25x6oc72fsf7pl5pxqipakzcual27u6db3njlq76p7jopna'
bucket_name = 'policy_log'
policy_name = 'politicapersonalizada'


def save_log(signer, body):
    object_storage = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    namespace = object_storage.get_namespace().data
    my_data = json.dumps(body)

    try:
        request = CreateBucketDetails()
        request.compartment_id = compartment_id
        request.name = bucket_name
        object_storage.create_bucket(namespace, request)
    except:
        print('erro')

    ts = str(datetime.utcnow().microsecond)
    object_name = 'log' + ts + str(randint(0, 10000))
    object_storage.put_object(namespace, bucket_name, object_name, my_data)

def zero_quota(signer, name, description):
    try:
        quotas_client = QuotasClient(config={}, signer=signer)
        statements = ["zero compute-core quota in tenancy", "zero block-storage quota in tenancy", "zero filesystem quota in tenancy", "zero database quota in tenancy"]
        new_quota = CreateQuotaDetails()
        new_quota.compartment_id = compartment_id
        new_quota.name = name
        new_quota.description = description
        new_quota.statements = statements
        quotas_client.create_quota(new_quota).data
        resp = { 'quota': 'Zerada com sucesso para compute, block-storage, database e filesystem'}
    except Exception as ex:
        resp = { 'quota': 'Ocorreu um erro: {}'.format(ex) }

    return resp

def create_policy(signer):
    identity = oci.identity.IdentityClient(config={}, signer=signer)
    try:
        new_pol = CreatePolicyDetails()
        new_pol.compartment_id = compartment_id
        new_pol.name = policy_name
        new_pol.description = "teste do teste"
        xpto_rule = "Allow dynamic-group exemplo to manage all-resources IN TENANCY"
        statements = [xpto_rule]
        new_pol.statements = statements
        identity.create_policy(new_pol)
        resp = { 'policies': 'politica {} criada com sucesso'.format(new_pol.name) }
    except Exception as ex:
        resp = { 'policies': 'Ocorreu um erro: {}'.format(ex) }
    return resp

def handler(ctx, data: io.BytesIO=None):
    signer = oci.auth.signers.get_resource_principals_signer()
    resp_policy = create_policy(signer)
    resp_quota = zero_quota(signer, 'new_quota', 'testing')
    resp = {'policies' : resp_policy, 'quotas' : resp_quota}
    save_log(signer, resp)
    return response.Response(
        ctx, response_data=json.dumps(resp), headers={"Content-Type": "application/json"}
    )