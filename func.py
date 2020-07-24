import io, os, oci, json, datetime
from random import randint
from fdk import response

compartmentId = 'ocid1.tenancy.oc1..aaaaaaaaqqzek25x6oc72fsf7pl5pxqipakzcual27u6db3njlq76p7jopna'
statement_list = ["zero compute-core quota in tenancy", "zero block-storage quota in tenancy", "zero filesystem quota in tenancy", "zero database quota in tenancy"]
bucket_name = 'br.se.quota.log.change'
policy_name = 'br.se.custom_policies'
quota_name = 'br.se.lock_main_services'
description = 'created by function serverless and event service'

def save_log(signer, body):
    object_storage = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    namespace = object_storage.get_namespace().data
    my_data = json.dumps(body)
    try:
        request = oci.object_storage.models.CreateBucketDetails()
        request.compartment_id = compartmentId
        request.name = bucket_name
        object_storage.create_bucket(namespace, request)
    except:
        print('bucket criado antes')

    ts = str(datetime.datetime.utcnow().microsecond)
    object_name = 'log' + ts + str(randint(0, 10000))
    object_storage.put_object(namespace, bucket_name, object_name, my_data)

def delete_quota(signer):
    quotas_client = oci.limits.QuotasClient(config={}, signer=signer)      
    quotas = quotas_client.list_quotas(compartment_id=compartmentId).data
    for quota in enumerate(quotas):
        quotas_client.delete_quota(quota_id=quota[1].id)

def zero_quota(signer):
    try:
        quotas_client = oci.limits.QuotasClient(config={}, signer=signer)
        statements = statement_list
        new_quota = oci.limits.models.CreateQuotaDetails()
        new_quota.compartment_id = compartmentId
        new_quota.name = quota_name
        new_quota.description = description
        new_quota.statements = statements
        quotas_client.create_quota(new_quota).data
        resp = { 'quota': 'Successfully change the quota to zero : compute, block-storage, database and filesystem'}
    except Exception as ex:
        resp = { 'quota': 'The cat went up on the roof: {}'.format(ex) }
    return resp

def create_quota(signer, budget, alert):
    alarm_forecast = budget.forecasted_spend / ((100 / alert[1].threshold))
    if (budget.actual_spend >= alarm_forecast):
        response = zero_quota(signer)
    else:
        delete_quota(signer)
        response = { 'quota' : 'You have budget to create new resources'}
    return response


def create_alert(budget_client, alert_rule):
    budget_client.delete_alert_rule(alert_rule[1].budget_id, alert_rule[1].id)
    rule_detail = oci.budget.models.CreateAlertRuleDetails()
    rule_detail.threshold = float(alert_rule[1].threshold) 
    rule_detail.threshold_type=alert_rule[1].threshold_type 
    rule_detail.type=alert_rule[1].type
    budget_client.create_alert_rule(alert_rule[1].budget_id, rule_detail)


def handler(ctx, data: io.BytesIO=None):
    signer = oci.auth.signers.get_resource_principals_signer()
    try:
        budget_client = oci.budget.BudgetClient(config={}, signer=signer)
        budgets = budget_client.list_budgets(compartment_id=compartmentId).data
        for budget in budgets:
            if (budget.forecasted_spend is not None):
                alerts = budget_client.list_alert_rules(budget.id).data
                if (len(alerts) != 0):
                    for alert in enumerate(alerts):
                        if (int(alert[1].threshold) == 1):
                            budget_client.delete_alert_rule(alert[1].budget_id, alert[1].id)
                            delete_quota(signer)
                            resp = {'Budgets Alert Rules and Quota': 'deleted! '}
                        else:
                            create_alert(budget_client, alert)
                            resp = create_quota(signer, budget, alert)
                else:
                    resp = {'Budgets Alert Rules': 'no alerts created'}
                    delete_quota(signer)
    except Exception as ex:
        resp = { 'Function': 'The cat went up on the roof: {}'.format(ex) }
    
    save_log(signer, resp)
    return response.Response(
        ctx, response_data=json.dumps(resp), headers={"Content-Type": "application/json"}
    )