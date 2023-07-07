import httpx
import time
import argparse
import prometheus_client
from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, GaugeMetricFamily

class MisskeyCollector(object):
    def __init__(self, host, token):
        self.host = host
        self.token = token

    def collect(self):
        get_online_users_count = httpx.post(f'{self.host}/api/get-online-users-count', json={}).json()
        yield GaugeMetricFamily('misskey_users_online', 'online users count', value=get_online_users_count['count'])

        stats = httpx.post(f'{self.host}/api/stats', json={}).json()
        yield GaugeMetricFamily('misskey_users_total', 'total users count', value=stats['originalUsersCount'])

        if self.token is not None:
            queue_stats = httpx.post(f'{self.host}/api/admin/queue/stats', json={'i': self.token}).json()
            for queue, stats in queue_stats.items():
                for stat, count in stats.items():
                    stat = stat.replace('-', '_')
                    yield GaugeMetricFamily(f'misskey_queue_{queue}_{stat}', f'{queue} {stat} count', value=count)

        ap_request = httpx.post(f'{self.host}/api/charts/ap-request', json={'span': 'hour', 'limit': 1}).json()
        yield GaugeMetricFamily(f'misskey_ap_deliver_failed', f'activitypub deliver failed count', value=ap_request['deliverFailed'][0])
        yield GaugeMetricFamily(f'misskey_ap_deliver_succeeded', f'activitypub deliver succeeded count', value=ap_request['deliverSucceeded'][0])
        yield GaugeMetricFamily(f'misskey_ap_inbox_received', f'activitypub inbox received count', value=ap_request['inboxReceived'][0])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog = 'misskey-exporter',
        description = 'Misskey Prometheus Exporter'
    )

    parser.add_argument(
        '--host',
        dest='host',
        required=True,
        help='Misskey URL to use API (Required)'
    )

    parser.add_argument(
        '--token',
        dest='token',
        required=False,
        help='API token to use authorization only api'
    )

    parser.add_argument(
        '-p', '--port',
        dest='port',
        type=int,
        default=9300,
        required=False,
        help='Binding port to access metrics (Default: 9300)'
    )

    args = parser.parse_args()

    REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
    REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
    REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)

    start_http_server(args.port)
    REGISTRY.register(MisskeyCollector(host=args.host, token=args.token))

    while True:
        time.sleep(5)
