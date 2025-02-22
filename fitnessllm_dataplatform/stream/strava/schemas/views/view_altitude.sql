select a.data as altitude, t.data as time, a.athlete_id, a.activity_id
from ${project}.${schema}.altitude a
inner join ${project}.${schema}.time t on t.athlete_id = a.athlete_id and t.activity_id = a.activity_id and t.index = a.index