zoom = 1
translate_x = 0
translate_y = 0
scroll_top = 0
scroll_left = 0

innard = document.getElementById("innard")

const scrollyDiv = document.getElementById('scrollable-box');

scrollyDiv.addEventListener('scroll', (e) => {
  scroll_top = e.target.scrollTop
  scroll_left = e.target.scrollLeft
})

function set_zoom(){
    return "scale(" + zoom + ") translate(" + translate_x + "px, " + translate_y + "px)"
}

function zoom_in() {
    if(zoom > 0.05){
        zoom += 0.05
    }
    else {
        zoom *= 2
    }
    innard.style.transformOrigin = `${translate_x + (innard.offsetWidth/2)} ${translate_y + (innard.offsetHeight/2)}`
    innard.style.transform = set_zoom()
}

function zoom_out() {
    if(zoom > 0.05){
        zoom -= 0.05
    }
    else {
        zoom /= 2
    }
    innard.style.transformOrigin = `${translate_x + (innard.offsetWidth/2)} ${translate_y + (innard.offsetHeight/2)}`
    innard.style.transform = set_zoom()
}

function reset_zoom() {
    zoom = 1
    translate_x = 0
    translate_y = 0
    innard.style.transform = set_zoom()
}
