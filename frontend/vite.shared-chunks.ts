export function vendorManualChunks(id: string): string | undefined {
  if (id.includes('node_modules/react-dom') || id.includes('node_modules/react-router')) return 'react-vendor'
  if (id.includes('node_modules/react/')) return 'react-vendor'
  if (id.includes('node_modules/aws-amplify') || id.includes('node_modules/@aws-amplify')) return 'amplify-vendor'
  if (id.includes('node_modules/lucide-react')) return 'lucide-vendor'
  return undefined
}
