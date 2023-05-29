using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using System.Net.Http;
using System.Text.Json.Nodes;
using Websocket.Client;

namespace WebApp1
{
    class Program
    {
        static async void run(string name,int join_game_id)
        {
            String Token = "";
            String game_id = join_game_id.ToString();
            { // incilize and get token
                HttpClient client = new HttpClient();
                String response1 = await client.GetStringAsync("http://localhost:8001/register/" + name + "/owner1");
                //Console.WriteLine(name + " " + response1);
                JsonNode IPlayer = JsonNode.Parse(response1);
                string str_id = IPlayer["id"].ToString();
                String response2 = await client.GetStringAsync("http://localhost:8001/token/game/" + game_id + "/player/" + str_id);
                //Console.WriteLine(name + " " + response2);
                JsonNode IToken = JsonNode.Parse(response2);
                Token = IToken["token"].ToString();
            }
            Console.WriteLine(name + " " + Token);


            var url = new Uri("ws://localhost:8001/ws/"+game_id);

            using (var client = new WebsocketClient(url))
            {
                var running = true;
                
                client.ReconnectTimeout = TimeSpan.FromSeconds(3000000);
                client.ReconnectionHappened.Subscribe(info =>Console.WriteLine($"Reconnection happened, type: {info.Type}"));

 
                client.Start();
                // Task.Run(() => client.Send("{'type':'wait'}"));
                var msg = new JsonObject { ["type"] = "Authorization", ["token"] = Token }.ToJsonString();
                client.Send(msg);
                Thread.Sleep(100);
                client.Send(new JsonObject { ["type"] = "wait"}.ToJsonString());

                client.MessageReceived.Subscribe(async MessageGameState => {
                    JsonNode GameState = JsonNode.Parse(MessageGameState.ToString());
                    

                    if (GameState["outcome"].ToString().Length>8)
                    {
                        running = false;
                        Console.WriteLine(GameState["outcome"].ToString());
                        return;

                    }

                    //your chess logic goes here

                    var move = GameState["legal_moves"][0];
                    Console.WriteLine(move.ToString());


                    client.Send(new JsonObject { ["type"] = "move and wait",["move"] = move.ToString() }.ToJsonString());

                });


                while (running)
                {
                    Thread.Sleep(100);
                }
                Console.WriteLine("THE END");
            }


        }


        static void Main(string[] args)
        {
            var r = new Random();
            int game = r.Next()%100;
            run("Adam", game);
            run("john", game);
            Console.WriteLine("start");
            Console.ReadKey();
        }
    }
}
