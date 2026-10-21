(function(){
  var btn=document.getElementById('siMenuBtn'), dd=document.getElementById('siDropdown');
  if(!btn||!dd) return;
  btn.addEventListener('click',function(){
    var open=dd.classList.toggle('open');
    btn.classList.toggle('open',open);
  });
})();
