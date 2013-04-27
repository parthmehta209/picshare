var VoteBox = function(options)
{
    var _this = this;
    _this.pollUrl = options.pollUrl;
    _this.newMessageUrl = options.newMessageUrl;
    //$('#startvote').submit(function() { _this.startVoting(); return false; });
    $('#voteyes').submit(function(){_this.voteYes(); return false;});
    $('#voteno').submit(function(){_this.voteNo(); return false;});
    _this.poll();
}

VoteBox.prototype.poll = function()
{
    var _this = this;
    var eventname  = window.location.pathname.split('/')[2];
    var callback = function(response)
    {
        var status = response.status[0];
        console.log("The polling returned status:"+response.status);
          
       
        if(status === 'voting')
        {
            $("#uploadpic").show();
            $("#voter").show(); 
            $("#responseRecorded").hide();
            $("#eventAborted").hide();
            $("#eventPublished").hide();
         
        }
        
        if(status === 'aborted')
        {
            
            $("#responseRecorded").hide();
            $("#eventAborted").show();
            $("#uploadpic").show();
            $("#voter").hide();
        }
        
        if(status === 'published')
        {
            $("#responseRecorded").hide();
            $("#eventAborted").hide();
            $("#eventPublished").show();
            $("#uploadpic").hide();
            $("#startvote").hide();
            $("#voter").hide();
        }
 
        var imagelist = response.status[1];
        console.log(imagelist);
        $('#images').empty();
        for(var i=0;i<imagelist.length;i++)
        {
            $('#images').append("<img src=/static/img/"+imagelist[i]+" class='img-polaroid' height='100' width='100'>");
        }
        
        setTimeout(function(){  _this.poll(); }, 0);
    }
    var url = '/poll/' + eventname;
    $.post(url, null, callback, "json");
}

VoteBox.prototype.voteYes = function()
{
    var _this = this;
    console.log("Vote Yes")
    $("#voter").hide();
    $("#responseRecorded").show();
    
    var callback = function(response)
    {
       console.log(response.success);
    }
    var party = window.location.pathname.split('/')[2];
    var url = '/vote/yes:'+party;
    $.post(url, null, callback, "json");
}

VoteBox.prototype.voteNo = function()
{
    var _this = this;
    console.log("voteNo")
    $("#voter").hide();
    $("#responseRecorded").show();
    var callback = function(response)
    {
       console.log(response.success);
    }
    var party = window.location.pathname.split('/')[2];
    var url = '/vote/no:'+party;
    $.post(url, null, callback, "json");
}

