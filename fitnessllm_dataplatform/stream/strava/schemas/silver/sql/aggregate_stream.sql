select CAST(t.index as INT64) as index,
       t.data as time,
       a.data as altitude,
       c.data as cadence,
       d.data as distance,
       gs.data as grade_smooth,
       hr.data as heartrate,
       ll.latitude,
       ll.longitude,
       p.data as power,
       m.data as moving,
       temp.data as temperature,
       vs.data as velocity_smooth,
       w.data as watts,
       act.name,
       act.sport_type,
       t.athlete_id,
       t.activity_id,
       CURRENT_TIMESTAMP() as bq_insert_timestamp
from {{ schema }}.time t
left join {{ schema }}.activity act on t.athlete_id = act.athlete_id and t.activity_id = act.activity_id
left join {{ schema }}.altitude a on t.athlete_id = a.athlete_id and t.activity_id = a.activity_id and t.index = a.index
left join {{ schema }}.cadence c on t.athlete_id = c.athlete_id and t.activity_id = c.activity_id and t.index = c.index
left join {{ schema }}.distance d on t.athlete_id = d.athlete_id and t.activity_id = d.activity_id and t.index = d.index
left join {{ schema }}.grade_smooth gs on t.athlete_id = gs.athlete_id and t.activity_id = gs.activity_id and t.index = gs.index
left join {{ schema }}.heartrate hr on t.athlete_id = hr.athlete_id and t.activity_id = hr.activity_id and t.index = hr.index
left join {{ schema }}.latlng ll on t.athlete_id = ll.athlete_id and t.activity_id = ll.activity_id and t.index = ll.index
left join {{ schema }}.moving m on t.athlete_id = m.athlete_id and t.activity_id = m.activity_id and t.index = m.index
left join {{ schema }}.power p on t.athlete_id = p.athlete_id and t.activity_id = p.activity_id and t.index = p.index
left join {{ schema }}.temp temp on t.athlete_id = temp.athlete_id and t.activity_id = temp.activity_id and t.index = temp.index
left join {{ schema }}.velocity_smooth vs on t.athlete_id = vs.athlete_id and t.activity_id = vs.activity_id and t.index = vs.index
left join {{ schema }}.watts w on t.athlete_id = w.athlete_id and t.activity_id = w.activity_id and t.index = w.index
where t.athlete_id = '{{ athlete_id }}'
{% if activity_id %}
and t.activity_id = '{{ activity_id }}'
{% endif %}
