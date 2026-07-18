export default function HealthPage() {
  return (
    <div>
      <h1>健康检查</h1>
      <p>状态：正常</p>
      <p>时间： {new Date().toISOString()}</p>
    </div>
  )
}
