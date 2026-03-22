from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import structlog

from app.database import get_collection
from app.core.deps import get_current_citizen, CurrentCitizen
from app.kafka.publisher import publish

log    = structlog.get_logger()
router = APIRouter()


class BinReportRequest(BaseModel):
    bin_serial:  str | None = None
    description: str
    lat:         float | None = None
    lon:         float | None = None
    photo_url:   str | None = None
    issue_type:  str = 'overflow'


class PickupRequest(BaseModel):
    item_type:    str
    description:  str | None = None
    address:      str
    lat:          float | None = None
    lon:          float | None = None
    photo_url:    str | None = None
    requested_date: str


@router.post('/report-bin', status_code=201)
async def report_bin(
    data:    BinReportRequest,
    citizen: CurrentCitizen = Depends(get_current_citizen),
):
    col        = get_collection('bin_reports')
    report_id  = str(uuid.uuid4())
    now        = datetime.now(timezone.utc).isoformat()

    doc = {
        '_id':         report_id,
        'citizen_id':  citizen.citizen_id,
        'bin_serial':  data.bin_serial,
        'description': data.description,
        'issue_type':  data.issue_type,
        'lat':         data.lat,
        'lon':         data.lon,
        'photo_url':   data.photo_url,
        'status':      'open',
        'created_at':  now,
    }
    await col.insert_one(doc)

    # Publish to Kafka so alert-service can create an alert
    publish('bin.citizen.report', report_id, {
        'report_id':   report_id,
        'citizen_id':  citizen.citizen_id,
        'bin_serial':  data.bin_serial,
        'description': data.description,
        'issue_type':  data.issue_type,
        'lat':         data.lat,
        'lon':         data.lon,
        'timestamp':   now,
    })

    log.info('bin.report.submitted',
             report_id=report_id,
             citizen_id=citizen.citizen_id)

    return {
        'report_id': report_id,
        'status':    'open',
        'message':   'Report submitted. Thank you for keeping Nairobi clean!',
    }


@router.get('/my-reports')
async def get_my_reports(
    citizen: CurrentCitizen = Depends(get_current_citizen),
):
    col  = get_collection('bin_reports')
    docs = await col.find(
        {'citizen_id': citizen.citizen_id}
    ).sort('created_at', -1).limit(20).to_list(20)
    for d in docs:
        d['id'] = d.pop('_id')
    return docs


@router.post('/pickup-request', status_code=201)
async def request_pickup(
    data:    PickupRequest,
    citizen: CurrentCitizen = Depends(get_current_citizen),
):
    col       = get_collection('pickup_requests')
    req_id    = str(uuid.uuid4())
    now       = datetime.now(timezone.utc).isoformat()

    doc = {
        '_id':            req_id,
        'citizen_id':     citizen.citizen_id,
        'item_type':      data.item_type,
        'description':    data.description,
        'address':        data.address,
        'lat':            data.lat,
        'lon':            data.lon,
        'photo_url':      data.photo_url,
        'requested_date': data.requested_date,
        'status':         'pending',
        'created_at':     now,
    }
    await col.insert_one(doc)

    log.info('pickup.requested',
             req_id=req_id,
             item_type=data.item_type)

    return {
        'request_id':     req_id,
        'status':         'pending',
        'requested_date': data.requested_date,
        'message':        'Pickup request submitted successfully',
    }
