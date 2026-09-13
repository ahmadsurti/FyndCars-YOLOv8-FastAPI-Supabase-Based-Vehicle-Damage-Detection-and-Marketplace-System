export function Navbar() {
  return (
    <nav aria-label="Brand" className="absolute top-3 left-4 sm:top-4 sm:left-5 z-20 pointer-events-auto select-none animate-navbar">
      <a href="/" aria-label="fynd(cars)" className="inline-flex items-baseline focus-visible:outline-none">
        <span className="font-comfortaa text-2xl sm:text-3xl font-bold tracking-tight text-white">fynd</span>
        <span className="font-instrument text-2xl sm:text-3xl font-normal text-white">(cars)</span>
      </a>
    </nav>
  )
}
