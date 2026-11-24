import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="border-t border-[#EAE8E3] bg-[#FAFAF7] py-8 text-xs text-[#7E7D77]">
      <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-16 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Copyright */}
        <div className="text-xs font-mono text-[#5A5955]">
          &copy; 2026 AEMA
        </div>

        {/* Center: Author Attribution */}
        <div className="text-xs text-[#7E7D77] text-center font-normal">
          Built by Sakshi Kasat &amp; Sumit Das
        </div>

        {/* Right Corner: Key Nav Links */}
        <div className="flex items-center gap-6 text-xs text-[#6B6A65]">
          <Link
            to="/docs"
            className="hover:text-[#141413] transition-colors"
          >
            Documentation
          </Link>
          <Link
            to="/research"
            className="hover:text-[#141413] transition-colors"
          >
            Research
          </Link>
          <Link
            to="/benchmarks"
            className="hover:text-[#141413] transition-colors"
          >
            Benchmarks
          </Link>
        </div>
      </div>
    </footer>
  )
}
