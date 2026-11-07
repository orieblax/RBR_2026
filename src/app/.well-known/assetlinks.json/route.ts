export async function GET() {
  const assetlinks = [
    {
      relation: ['delegate_permission/common.handle_all_urls'],
      target: {
        namespace: 'android_app',
        package_name: 'com.rbrfinance.app',
        sha256_cert_fingerprints: [
          '14:6D:E9:7F:0F:52:EA:CB:5B:61:99:40:8A:26:5F:A7:24:D0:65:70:E1:FF:A7:F9:64:99:93:15:35:54:19:D8',
        ],
      },
    },
  ];

  return new Response(JSON.stringify(assetlinks), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=86400',
    },
  });
}
