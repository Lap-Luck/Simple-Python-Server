extends Node

class MyWeb:
	var http:HTTPRequest
	var out_txt=null
	var sem:Semaphore
	func _init(node:Node):
		sem=Semaphore.new()
		self.http=HTTPRequest.new()
		node.add_child(http)
		self.http.connect("request_completed", self, "_http_request_completed")
	func send(method,host):
		http.request(host, [], true, method, "")
	func recv():
		if out_txt == null:
			sem.wait()
			sem=Semaphore.new()
			var o=out_txt
			self.out_txt = null
			return o
		else:
			sem=Semaphore.new()
			var o=out_txt
			self.out_txt = null
			return o
	func _http_request_completed(result, response_code, headers, body):
		self.out_txt=body.get_string_from_utf8()
		sem.post()





func _ready():
	Thread.new().start(self,"main")
	
func main():
	print("##########")
	var web=MyWeb.new(self)
	web.send(HTTPClient.METHOD_POST,'http://127.0.0.1:8001/register/N_GD/owner')
	var id=parse_json(web.recv())['id']
	print("##########")
	web.send(HTTPClient.METHOD_POST,'http://127.0.0.1:8001/games/100/tokens/'+String(id))
	var token=parse_json(web.recv())
	print(token['token'])
	print("##########")
	var ws=WebSocketClient.new()
	print("**********")
	var err=ws.connect_to_url('ws://127.0.0.1:8001/ws/', PoolStringArray(  ),false,
			PoolStringArray([
				#to_json({'Authorization':token['token']})
				
				])
			)
	assert(err==OK)
	print("**********")
	
	var msg=to_json({'type':'connect','id':id}).to_ascii()
	ws.poll()
	ws.put_packet(msg)
	print("**********")
	OS.delay_msec(30)
	ws.poll()
	OS.delay_msec(30)
	print("**********")
	var p=ws.get_packet()
	var t=p.get_string_from_ascii()
	print(t)
















