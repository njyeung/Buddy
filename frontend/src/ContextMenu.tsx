export default function Modal({setOpened, children }: { setOpened: React.Dispatch<React.SetStateAction<boolean>>, children: React.ReactNode }) {

  return <section>
    <div
    onMouseDown={() => setOpened(false)}
    style={{
      animation: 'fade-in 200ms ease-out'
    }} 
    className="absolute top-0 left-0 w-full h-full bg-black/30 z-[999]">
      <div className="flex w-full h-full items-center justify-center p-5">
        <div
        style={{
          animation: 'pop-in 120ms ease-out'
        }} 
        onMouseDown={(e) => e.stopPropagation()}
        className="w-full max-w-[400px] h-[500px] bg-zinc-900 rounded-lg p-2">
          <div className="w-full h-full rounded-lg border-2 border-primary-200 p-5">
            { children }
          </div>
        </div>
      </div>
    </div>
  </section> 
}