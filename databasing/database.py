from sqlalchemy import create_engine
import pandas as pd
from numpy import abs, round
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError

from db_conn_strings import aws_conn_string

# TODO: move this in to the proper functions
# Global for now. Should be fixed..
conn = create_engine(aws_conn_string)


def push_to_db(header, content):
    if header is not None:
        print 'pushing collar metadata to db...'
        try:
            header.to_sql('athlete_lift', conn, if_exists='append', index=False, index_label='lift_id')
        except OperationalError, e:
            print '!!!!!Could not push collar metadata to database!!!!'
            print 'Likely because PostgreSQL server not running.\nError message: {}'.format(e)
            print 'skipping push to athlete_lift and resuming MQTT listening'
            return None
        except IntegrityError, e:
            print '!!!!! Could not push collar metadata to database !!!!!'
            print 'Likely because lift_id already exists in athlete_lift. \nError message: {}'.format(e)
            print 'Moving forward without pushing header into athlete_lift...'
        else:
            print 'collar metadata push successful. moving on to pushing content...'

    if content is not None:
        lift_id = content.lift_id.unique()[0]
        try:
            ts = pd.read_sql('SELECT timepoint::DOUBLE PRECISION FROM lift_data WHERE lift_id = {id} ORDER BY timepoint DESC LIMIT 2'.format(id=lift_id), conn)['timepoint']
            # NOTE: Console prints max_t = 19.89999999999999 - will this cause a rounding error??
            if len(ts) > 1:
                max_t = float(round(max(ts), 2))
                delta_t = abs(ts[1] - ts[0])
                print 'lift_id: {id}, max_t: {t}'.format(id=lift_id, t=max_t)
                if max_t is None:
                    max_t = 0.
            else:
                max_t = 0.
                delta_t = 0.
        except ProgrammingError:
            print 'table lift_data does not exist...'
            max_t = 0.
            delta_t = 0.

        content.timepoint += (max_t + delta_t)  # Have to step up from max_t because timepoint[0] = 0
        print 'pushing new content values to db...'
        content.to_sql('lift_data', conn, if_exists='append', index=False, index_label=['lift_id', 'timepoint'])
        print 'done'
